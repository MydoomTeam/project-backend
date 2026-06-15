from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RegistrationModel(Base):
    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("tournament_id", "player_id", name="uq_registration_torneo_jugador"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="Confirmado")
    registration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    elo_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
