from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RegistrationModel(Base):
    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("torneo_id", "jugador_id", name="uq_registration_torneo_jugador"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    torneo_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), nullable=False)
    jugador_id: Mapped[int] = mapped_column(ForeignKey("jugador.id"), nullable=False)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default="Confirmado")
