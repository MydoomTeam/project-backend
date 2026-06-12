from sqlalchemy import Column, Date, ForeignKey, Integer, Text
from sqlalchemy.schema import Identity

from app.core.database import Base


class ScheduledMatch(Base):
    __tablename__ = "scheduled_matches"

    id = Column(Integer, Identity(), primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)
    match_siguiente_id = Column(Integer, nullable=True)
    estado_match = Column(Text, nullable=False)
    marcador_detalle = Column(Text, nullable=False)
    fecha_hora_programada = Column(Date, nullable=False)
    resultado = Column(Text, nullable=True)
