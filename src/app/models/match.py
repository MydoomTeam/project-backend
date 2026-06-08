from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MatchModel(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    torneo_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), nullable=False)
    ronda: Mapped[int] = mapped_column(Integer, nullable=False)
    posicion: Mapped[int] = mapped_column(Integer, nullable=False)
    jugador1_id: Mapped[int | None] = mapped_column(ForeignKey("jugador.id"), nullable=True)
    jugador2_id: Mapped[int | None] = mapped_column(ForeignKey("jugador.id"), nullable=True)
    ganador_id: Mapped[int | None] = mapped_column(ForeignKey("jugador.id"), nullable=True)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default="Pendiente")
