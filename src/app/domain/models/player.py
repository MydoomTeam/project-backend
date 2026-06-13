from sqlalchemy import Column, Date, Integer, Text
from sqlalchemy.schema import Identity

from app.core.database import Base


class Player(Base):
    __tablename__ = "jugador"

    id = Column(Integer, Identity(), primary_key=True)
    nombre_usuario = Column(Text, nullable=False)
    correo_electronico = Column(Text, nullable=False)
    contrasena_hash = Column(Text, nullable=False)
    rol = Column(Text, nullable=False)
    fecha_ultimo_acceso = Column(Date, nullable=False)
    elo_global = Column(Integer, nullable=False)
