from sqlalchemy import Column, Date, Integer, Text
from sqlalchemy.schema import Identity

from app.core.database import Base


class Enfrentamiento(Base):
    __tablename__ = "enfrentamiento"

    id = Column(Integer, Identity(), primary_key=True)
    ronda_id = Column(Integer, nullable=False)
    inscripcion_a_id = Column(Integer, nullable=False)
    inscripcion_b_id = Column(Integer, nullable=False)
    match_siguiente_id = Column(Integer, nullable=True)
    estado_match = Column(Text, nullable=False)
    marcador_detalle = Column(Text, nullable=False)
    fecha_hora_programada = Column(Date, nullable=False)
    resultado = Column(Text, nullable=True)
