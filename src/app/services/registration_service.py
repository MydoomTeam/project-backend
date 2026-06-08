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

    def registrar_inscripcion(self, data: RegistrationCreate, jugador_id: int) -> RegistrationModel:
        torneo = self.tournament_repo.obtener_por_id(data.torneo_id)
        if torneo is None or torneo.estado != "Pendiente":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El torneo no existe o no está disponible para inscripción",
            )

        if jugador_id == torneo.creador_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El administrador del torneo no puede inscribirse como participante",
            )

        if self.registration_repo.existe_inscripcion_activa(data.torneo_id, jugador_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El jugador ya está inscrito en este torneo",
            )

        inscripcion = RegistrationModel(
            torneo_id=data.torneo_id,
            jugador_id=jugador_id,
            estado="Confirmado",
        )
        return self.registration_repo.guardar(inscripcion)
