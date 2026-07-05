from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.tournament import TournamentModel
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.tournament_repository import TournamentRepository
from app.schemas.tournament import TournamentCreate, TournamentDetailResponse

_MAX_ROUNDS_BY_FORMAT: dict[str, int] = {
    "Eliminación Sencilla": 7,
    "Eliminación Doble":    5,
    "Round Robin":          3,
    "Swiss":                7,
}


class TournamentService:
    def __init__(self, db: Session):
        self.repo = TournamentRepository(db)
        self.audit_repo = AuditLogRepository(db)

    def _log_audit(self, actor_id: int, action: str, change_description: str) -> None:
        if hasattr(self.audit_repo, "log_action"):
            self._log_with_log_action(actor_id, action, change_description)
            return

        self._log_with_record(action, actor_id, change_description)

    def _log_with_log_action(self, actor_id: int, action: str, change_description: str) -> None:
        self.audit_repo.log_action(
            actor_id=actor_id,
            action=action,
            change_description=change_description,
        )

    def _log_with_record(self, action: str, actor_id: int, change_description: str) -> None:
        try:
            self.audit_repo.record(action, actor_id, datetime.now(), change_description)
        except TypeError:
            self.audit_repo.record(action, actor_id, datetime.now())

    @staticmethod
    def _tournament_payload_keys() -> tuple[str, ...]:
        return (
            "id",
            "name",
            "elimination_type",
            "game_name",
            "game_category",
            "participant_target",
            "rounds",
            "round_duration_minutes",
            "uses_score",
            "status",
            "start_date",
            "end_date",
            "language",
            "region",
            "creator_id",
        )

    @staticmethod
    def _to_tournament_payload(
        tournament: TournamentModel,
        creator_name: str | None = None,
        creator_avatar_url: str | None = None,
    ) -> dict:
        payload = {key: getattr(tournament, key) for key in TournamentService._tournament_payload_keys()}
        payload["creator_name"] = creator_name
        payload["creator_avatar_url"] = creator_avatar_url
        return payload

    @staticmethod
    def _build_tournament_detail(
        tournament: TournamentModel,
        creator_name: str,
        creator_avatar_url: str | None,
        total_participants: int,
    ) -> TournamentDetailResponse:
        payload = TournamentService._to_tournament_payload(tournament, creator_name, creator_avatar_url)
        payload["total_participants"] = total_participants
        return TournamentDetailResponse(**payload)

    def _get_existing_tournament(self, tournament_id: int) -> TournamentModel:
        tournament = self.repo.get_by_id(tournament_id)
        if tournament is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Torneo no encontrado",
            )
        return tournament

    @staticmethod
    def _ensure_creator_is_admin(tournament: TournamentModel, admin_id: int) -> None:
        if tournament.creator_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede cancelar el torneo",
            )

    @staticmethod
    def _ensure_tournament_is_cancellable(status_value: str) -> None:
        if status_value not in ("Pendiente", "Listo para iniciar"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede cancelar un torneo en estado Pendiente o Listo para iniciar",
            )

    def _validate_rounds_for_format(self, data: TournamentCreate) -> None:
        max_rounds = _MAX_ROUNDS_BY_FORMAT.get(data.elimination_type)
        if max_rounds is None:
            formats = list(_MAX_ROUNDS_BY_FORMAT)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato '{data.elimination_type}' no reconocido. Válidos: {formats}",
            )

        if data.rounds > max_rounds:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{data.elimination_type}' admite máximo {max_rounds} rondas",
            )

    def _ensure_name_is_available(self, name: str) -> None:
        existing = self.repo.get_active_by_name(name)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un torneo activo con ese nombre",
            )

    @staticmethod
    def _build_tournament(data: TournamentCreate, creator_id: int) -> TournamentModel:
        return TournamentModel(
            name=data.name,
            elimination_type=data.elimination_type,
            game_name=data.game_name,
            game_category=data.game_category,
            participant_target=data.participant_target,
            rounds=data.rounds,
            round_duration_minutes=data.round_duration_minutes,
            uses_score=data.uses_score,
            status="Pendiente",
            start_date=data.start_date,
            end_date=data.end_date,
            language=data.language,
            region=data.region,
            creator_id=creator_id,
        )

    def get_available_tournaments(self) -> list[dict]:
        rows = self.repo.list_available_with_creator()
        return [
            self._to_tournament_payload(tournament, creator_name, creator_avatar_url)
            for tournament, creator_name, creator_avatar_url in rows
        ]

    def get_all_tournaments(self) -> list[dict]:
        rows = self.repo.list_all_with_creator()
        return [
            self._to_tournament_payload(tournament, creator_name, creator_avatar_url)
            for tournament, creator_name, creator_avatar_url in rows
        ]

    def get_tournament_detail(self, tournament_id: int) -> TournamentDetailResponse:
        result = self.repo.get_detail_with_creator(tournament_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Torneo no encontrado",
            )
        tournament, creator_name, creator_avatar_url, total_participants = result
        return self._build_tournament_detail(
            tournament=tournament,
            creator_name=creator_name,
            creator_avatar_url=creator_avatar_url,
            total_participants=total_participants,
        )

    def cancel_tournament(self, tournament_id: int, admin_id: int) -> None:
        tournament = self._get_existing_tournament(tournament_id)
        self._ensure_creator_is_admin(tournament, admin_id)
        self._ensure_tournament_is_cancellable(tournament.status)
        self.audit_repo.record(
            action="CANCELAR_TORNEO",
            user_id=admin_id,
            created_at=datetime.now(),
            change_description=f"tournament_id={tournament_id}",
        )
        self.repo.delete(tournament)

    def create_tournament(self, data: TournamentCreate, creator_id: int) -> TournamentModel:
        self._validate_rounds_for_format(data)
        self._ensure_name_is_available(data.name)

        tournament = self._build_tournament(data, creator_id)
        created = self.repo.save(tournament)
        self._log_audit(
            actor_id=creator_id,
            action="CREAR_TORNEO",
            change_description=f"tournament_id={created.id}",
        )
        return created
