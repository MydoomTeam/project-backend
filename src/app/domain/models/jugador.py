from sqlalchemy import Column, Date, Integer, Text

from app.core.database import Base


class Jugador(Base):
    __tablename__ = "jugador"

    id = Column(Integer, primary_key=True, autoincrement=False)
    nombre_usuario = Column(Text, nullable=False)
    correo_electronico = Column(Text, nullable=False)
    contrasena_hash = Column(Text, nullable=False)
    rol = Column(Text, nullable=False)
    fecha_ultimo_acceso = Column(Date, nullable=False)
    elo_global = Column(Integer, nullable=False)
