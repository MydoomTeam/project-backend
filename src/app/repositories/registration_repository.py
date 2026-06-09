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

    def obtener_inscripcion_activa(self, torneo_id: int, jugador_id: int) -> RegistrationModel | None:
        stmt = select(RegistrationModel).where(
            RegistrationModel.torneo_id == torneo_id,
            RegistrationModel.jugador_id == jugador_id,
            RegistrationModel.estado == "Confirmado",
        )
        return self.db.execute(stmt).scalars().first()

    def obtener_inscripcion(self, torneo_id: int, jugador_id: int) -> RegistrationModel | None:
        stmt = select(RegistrationModel).where(
            RegistrationModel.torneo_id == torneo_id,
            RegistrationModel.jugador_id == jugador_id,
        )
        return self.db.execute(stmt).scalars().first()

    def reactivar(self, inscripcion: RegistrationModel) -> RegistrationModel:
        inscripcion.estado = "Confirmado"
        self.db.commit()
        self.db.refresh(inscripcion)
        return inscripcion

    def cancelar(self, inscripcion: RegistrationModel) -> None:
        inscripcion.estado = "Cancelada"
        self.db.commit()
