from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.player import Player
from app.models.registration import RegistrationModel


class RegistrationRepository:
    def __init__(self, db: Session):
        self.db = db

    def active_registration_exists(self, tournament_id: int, player_id: int) -> bool:
        stmt = select(RegistrationModel).where(
            RegistrationModel.tournament_id == tournament_id,
            RegistrationModel.player_id == player_id,
            RegistrationModel.status == "Confirmado",
        )
        return self.db.execute(stmt).scalars().first() is not None

    def save(self, registration: RegistrationModel) -> RegistrationModel:
        self.db.add(registration)
        self.db.commit()
        self.db.refresh(registration)
        return registration

    def get_active_registration(self, tournament_id: int, player_id: int) -> RegistrationModel | None:
        stmt = select(RegistrationModel).where(
            RegistrationModel.tournament_id == tournament_id,
            RegistrationModel.player_id == player_id,
            RegistrationModel.status == "Confirmado",
        )
        return self.db.execute(stmt).scalars().first()

    def get_registration(self, tournament_id: int, player_id: int) -> RegistrationModel | None:
        stmt = select(RegistrationModel).where(
            RegistrationModel.tournament_id == tournament_id,
            RegistrationModel.player_id == player_id,
        )
        return self.db.execute(stmt).scalars().first()

    def reactivate(self, registration: RegistrationModel) -> RegistrationModel:
        registration.status = "Confirmado"
        self.db.commit()
        self.db.refresh(registration)
        return registration

    def cancel(self, registration: RegistrationModel) -> None:
        registration.status = "Cancelada"
        self.db.commit()

    def list_by_tournament(self, tournament_id: int) -> list[tuple[RegistrationModel, str, str]]:
        stmt = (
            select(RegistrationModel, Player.username, Player.email)
            .join(Player, Player.id == RegistrationModel.player_id)
            .where(RegistrationModel.tournament_id == tournament_id)
            .order_by(RegistrationModel.id.asc())
        )
        return list(self.db.execute(stmt).all())

    def update_status(self, registration: RegistrationModel, new_status: str) -> RegistrationModel:
        registration.status = new_status
        self.db.commit()
        self.db.refresh(registration)
        return registration
