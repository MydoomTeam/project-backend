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

    def get_available_tournaments(self) -> list[TournamentModel]:
        return self.repo.list_available()

    def get_all_tournaments(self) -> list[TournamentModel]:
        return self.repo.list_all()

    def get_tournament_detail(self, tournament_id: int) -> TournamentDetailResponse:
        result = self.repo.get_detail_with_creator(tournament_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Torneo no encontrado",
            )
        tournament, creator_name, total_participants = result
        return TournamentDetailResponse(
            id=tournament.id,
            name=tournament.name,
            elimination_type=tournament.elimination_type,
            game_name=tournament.game_name,
            game_category=tournament.game_category,
            participant_target=tournament.participant_target,
            rounds=tournament.rounds,
            round_duration_minutes=tournament.round_duration_minutes,
            status=tournament.status,
            start_date=tournament.start_date,
            end_date=tournament.end_date,
            language=tournament.language,
            region=tournament.region,
            creator_id=tournament.creator_id,
            creator_name=creator_name,
            total_participants=total_participants,
        )

    def cancel_tournament(self, tournament_id: int, admin_id: int) -> None:
        tournament = self.repo.get_by_id(tournament_id)
        if tournament is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Torneo no encontrado",
            )
        if tournament.creator_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede cancelar el torneo",
            )
        if tournament.status not in ("Pendiente", "Listo para iniciar"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede cancelar un torneo en estado Pendiente o Listo para iniciar",
            )
        self.audit_repo.record(action="CANCELAR_TORNEO", user_id=admin_id, created_at=datetime.now())
        self.repo.delete(tournament)

    def create_tournament(self, data: TournamentCreate, creator_id: int) -> TournamentModel:
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

        existing = self.repo.get_active_by_name(data.name)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un torneo activo con ese nombre",
            )

        tournament = TournamentModel(
            name=data.name,
            elimination_type=data.elimination_type,
            game_name=data.game_name,
            game_category=data.game_category,
            participant_target=data.participant_target,
            rounds=data.rounds,
            round_duration_minutes=data.round_duration_minutes,
            status="Pendiente",
            start_date=data.start_date,
            end_date=data.end_date,
            language=data.language,
            region=data.region,
            creator_id=creator_id,
        )
        self.audit_repo.record(action="CREAR_TORNEO", user_id=creator_id, created_at=datetime.now())
        return self.repo.save(tournament)
