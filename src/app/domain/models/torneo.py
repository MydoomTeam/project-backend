from sqlalchemy import Column, Date, Integer, Text
from sqlalchemy.schema import Identity

from app.core.database import Base


class Torneo(Base):
    __tablename__ = "torneo"

    id = Column(Integer, Identity(), primary_key=True)
    administrador_id = Column(Integer, nullable=False)
    nombre = Column(Text, nullable=False)
    tipo_eliminacion = Column(Text, nullable=False)
    nombre_juego = Column(Text, nullable=False)
    categoria_juego = Column(Text, nullable=False)
    numero_participantes = Column(Integer, nullable=False)
    numero_rondas = Column(Integer, nullable=False)
    duracion_ronda = Column(Integer, nullable=False)
    estado = Column(Text, nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=True)
    idioma = Column(Text, nullable=True)
    region = Column(Text, nullable=True)
