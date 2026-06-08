from sqlalchemy import Column, Date, Integer, Text
from sqlalchemy.schema import Identity

from app.core.database import Base


class Inscripcion(Base):
    __tablename__ = "inscripcion"

    id = Column(Integer, Identity(), primary_key=True)
    torneo_id = Column(Integer, nullable=False)
    jugador_id = Column(Integer, nullable=False)
    estado_participante = Column(Text, nullable=False)
    fecha_inscripcion = Column(Date, nullable=False)
    elo_seed = Column(Integer, nullable=True)
