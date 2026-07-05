from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.registration import RegistrationModel
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.registration_repository import RegistrationRepository
from app.repositories.tournament_repository import TournamentRepository
from app.schemas.registration import RegistrationListItem

_REGISTRATION_PENDING = "Por confirmar"
_REGISTRATION_CONFIRMED = "Confirmado"
_REGISTRATION_REJECTED = "Rechazado"
_REGISTRATION_CANCELLED = "Cancelada"
_VALID_ADMIN_STATUSES = {_REGISTRATION_CONFIRMED, _REGISTRATION_REJECTED}


class RegistrationService:
    def __init__(self, db: Session):
        self.registration_repo = RegistrationRepository(db)
        self.tournament_repo = TournamentRepository(db)
        self.audit_repo = AuditLogRepository(db)

    def _get_existing_tournament(self, tournament_id: int):
        tournament = self.tournament_repo.get_by_id(tournament_id)
        if tournament is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Torneo no encontrado",
            )
        return tournament

    @staticmethod
    def _ensure_admin_is_creator(tournament, admin_id: int) -> None:
        if tournament.creator_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede gestionar participantes",
            )

    @staticmethod
    def _to_registration_item(registration, username: str, email: str) -> RegistrationListItem:
        return RegistrationListItem(
            id=registration.id,
            tournament_id=registration.tournament_id,
            player_id=registration.player_id,
            username=username,
            email=email,
            status=registration.status,
            registration_date=registration.registration_date,
            elo_seed=registration.elo_seed,
        )

    @staticmethod
    def _ensure_tournament_open_for_registration(tournament) -> None:
        if tournament is None or tournament.status != "Pendiente":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El torneo no existe o no está disponible para inscripción",
            )

    @staticmethod
    def _ensure_player_is_not_creator(player_id: int, creator_id: int) -> None:
        if player_id == creator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El administrador del torneo no puede inscribirse como participante",
            )

    def _ensure_no_active_registration(self, tournament_id: int, player_id: int) -> None:
        if self.registration_repo.active_registration_exists(tournament_id, player_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El jugador ya está inscrito en este torneo",
            )

    def _save_new_registration(self, tournament_id: int, player_id: int) -> RegistrationModel:
        registration = RegistrationModel(
            tournament_id=tournament_id,
            player_id=player_id,
            status=_REGISTRATION_PENDING,
            registration_date=date.today(),
        )
        return self.registration_repo.save(registration)

    @staticmethod
    def _ensure_tournament_pending_for_admin_action(tournament_status: str) -> None:
        if tournament_status != "Pendiente":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo puedes gestionar participantes en estado Pendiente",
            )

    @staticmethod
    def _ensure_status_is_allowed(status_value: str) -> None:
        if status_value not in _VALID_ADMIN_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Estado de inscripción no permitido",
            )

    @staticmethod
    def _ensure_registration_is_updatable(registration) -> None:
        if registration is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inscripción no encontrada")
        if registration.status == _REGISTRATION_CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede actualizar una inscripción cancelada",
            )

    def _log_update_status_audit(
        self,
        tournament_id: int,
        player_id: int,
        status_value: str,
        admin_id: int,
    ) -> None:
        self.audit_repo.log_action(
            actor_id=admin_id,
            action="UPDATE_REGISTRATION_STATUS",
            change_description=f"Tournament:{tournament_id}:Player:{player_id}:{status_value}",
        )

    def register(self, tournament_id: int, player_id: int) -> RegistrationModel:
        tournament = self.tournament_repo.get_by_id(tournament_id)
        self._ensure_tournament_open_for_registration(tournament)
        self._ensure_player_is_not_creator(player_id, tournament.creator_id)
        self._ensure_no_active_registration(tournament_id, player_id)

        existing = self.registration_repo.get_registration(tournament_id, player_id)
        if existing is not None:
            existing.status = _REGISTRATION_PENDING
            return self.registration_repo.update_status(existing, _REGISTRATION_PENDING)

        return self._save_new_registration(tournament_id, player_id)

    def cancel_registration(self, tournament_id: int, player_id: int) -> None:
        tournament = self.tournament_repo.get_by_id(tournament_id)
        if tournament is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Torneo no encontrado",
            )
        if tournament.status != "Pendiente":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo puedes desinscribirte de un torneo en estado Pendiente",
            )
        registration = self.registration_repo.get_registration(tournament_id, player_id)
        if registration is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No estás inscrito en este torneo",
            )
        self.registration_repo.cancel(registration)

    def list_tournament_registrations(self, tournament_id: int, admin_id: int) -> list[RegistrationListItem]:
        tournament = self._get_existing_tournament(tournament_id)
        self._ensure_admin_is_creator(tournament, admin_id)

        rows = self.registration_repo.list_by_tournament(tournament_id)
        return [self._to_registration_item(registration, username, email) for registration, username, email in rows]

    def update_registration_status(
        self,
        tournament_id: int,
        player_id: int,
        status_value: str,
        admin_id: int,
    ) -> RegistrationModel:
        tournament = self._get_existing_tournament(tournament_id)
        self._ensure_admin_is_creator(tournament, admin_id)
        self._ensure_tournament_pending_for_admin_action(tournament.status)
        self._ensure_status_is_allowed(status_value)

        registration = self.registration_repo.get_registration(tournament_id, player_id)
        self._ensure_registration_is_updatable(registration)

        updated = self.registration_repo.update_status(registration, status_value)
        self._log_update_status_audit(tournament_id, player_id, status_value, admin_id)
        return updated
