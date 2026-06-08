from sqlalchemy import Column, Date, Integer
from sqlalchemy.schema import Identity

from app.core.database import Base


class HistorialElo(Base):
    __tablename__ = "historialelo"

    id = Column(Integer, Identity(), primary_key=True)
    enfrentamiento_id = Column(Integer, nullable=False)
    jugador_id = Column(Integer, nullable=False)
    valor_elo_anterior = Column(Integer, nullable=False)
    valor_elo_actual = Column(Integer, nullable=False)
    fecha_cambio = Column(Date, nullable=False)
