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

    def save(self, registration: RegistrationModel) -> RegistrationModel:
        self.db.add(registration)
        self.db.commit()
        self.db.refresh(registration)
        return registration

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

    def reactivate(self, registration: RegistrationModel) -> RegistrationModel:
        registration.estado = "Confirmado"
        self.db.commit()
        self.db.refresh(registration)
        return registration

    def cancel(self, registration: RegistrationModel) -> None:
        registration.estado = "Cancelada"
        self.db.commit()
