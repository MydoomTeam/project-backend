from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.registration import RegistrationModel
from app.repositories.registration_repository import RegistrationRepository
from app.repositories.tournament_repository import TournamentRepository
from app.schemas.registration import RegistrationCreate


class RegistrationService:
    def __init__(self, db: Session):
        self.registration_repo = RegistrationRepository(db)
        self.tournament_repo = TournamentRepository(db)

    def register(self, data: RegistrationCreate, player_id: int) -> RegistrationModel:
        tournament = self.tournament_repo.get_by_id(data.tournament_id)
        if tournament is None or tournament.status != "Pendiente":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El torneo no existe o no está disponible para inscripción",
            )

        if player_id == tournament.creator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El administrador del torneo no puede inscribirse como participante",
            )

        if self.registration_repo.active_registration_exists(data.tournament_id, player_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El jugador ya está inscrito en este torneo",
            )

        existing = self.registration_repo.get_registration(data.tournament_id, player_id)
        if existing is not None:
            return self.registration_repo.reactivate(existing)

        registration = RegistrationModel(
            tournament_id=data.tournament_id,
            player_id=player_id,
            status="Confirmado",
        )
        return self.registration_repo.save(registration)

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
        registration = self.registration_repo.get_active_registration(tournament_id, player_id)
        if registration is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No estás inscrito en este torneo",
            )
        self.registration_repo.cancel(registration)
