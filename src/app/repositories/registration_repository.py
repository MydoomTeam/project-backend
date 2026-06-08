from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.registration import RegistrationModel


class RegistrationRepository:
    def __init__(self, db: Session):
        self.db = db

    def existe_inscripcion_activa(self, torneo_id: int, jugador_id: int) -> bool:
        stmt = select(RegistrationModel).where(
            RegistrationModel.torneo_id == torneo_id,
            RegistrationModel.jugador_id == jugador_id,
            RegistrationModel.estado == "Confirmado",
        )
        return self.db.execute(stmt).scalars().first() is not None

    def guardar(self, inscripcion: RegistrationModel) -> RegistrationModel:
        self.db.add(inscripcion)
        self.db.commit()
        self.db.refresh(inscripcion)
        return inscripcion
