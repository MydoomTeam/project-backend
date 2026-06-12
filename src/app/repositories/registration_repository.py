from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.registration import RegistrationModel


class RegistrationRepository:
    def __init__(self, db: Session):
        self.db = db

    def active_registration_exists(self, torneo_id: int, jugador_id: int) -> bool:
        stmt = select(RegistrationModel).where(
            RegistrationModel.torneo_id == torneo_id,
            RegistrationModel.jugador_id == jugador_id,
            RegistrationModel.estado == "Confirmado",
        )
        return self.db.execute(stmt).scalars().first() is not None

    def save(self, inscripcion: RegistrationModel) -> RegistrationModel:
        self.db.add(inscripcion)
        self.db.commit()
        self.db.refresh(inscripcion)
        return inscripcion

    def get_active_registration(self, torneo_id: int, jugador_id: int) -> RegistrationModel | None:
        stmt = select(RegistrationModel).where(
            RegistrationModel.torneo_id == torneo_id,
            RegistrationModel.jugador_id == jugador_id,
            RegistrationModel.estado == "Confirmado",
        )
        return self.db.execute(stmt).scalars().first()

    def get_registration(self, torneo_id: int, jugador_id: int) -> RegistrationModel | None:
        stmt = select(RegistrationModel).where(
            RegistrationModel.torneo_id == torneo_id,
            RegistrationModel.jugador_id == jugador_id,
        )
        return self.db.execute(stmt).scalars().first()

    def reactivate(self, inscripcion: RegistrationModel) -> RegistrationModel:
        inscripcion.estado = "Confirmado"
        self.db.commit()
        self.db.refresh(inscripcion)
        return inscripcion

    def cancel(self, inscripcion: RegistrationModel) -> None:
        inscripcion.estado = "Cancelada"
        self.db.commit()
