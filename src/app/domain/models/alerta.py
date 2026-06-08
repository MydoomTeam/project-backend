from sqlalchemy import Column, Date, Integer, Text
from sqlalchemy.schema import Identity

from app.core.database import Base


class Alerta(Base):
    __tablename__ = "alerta"

    id = Column(Integer, Identity(), primary_key=True)
    administrador_id = Column(Integer, nullable=True)
    jugador_id = Column(Integer, nullable=True)
    tipo_evento = Column(Text, nullable=False)
    mensaje = Column(Text, nullable=False)
    fecha_hora = Column(Date, nullable=False)
    estado_lectura = Column(Text, nullable=False)
