from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TournamentModel(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    tipo_eliminacion: Mapped[str] = mapped_column(Text, nullable=False)
    rondas: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default="Pendiente")
    creador_id: Mapped[int] = mapped_column(ForeignKey("jugador.id"), nullable=False)
