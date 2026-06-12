from sqlalchemy import Column, Date, Integer, Text
from sqlalchemy.schema import Identity

from app.core.database import Base


class LogAuditoria(Base):
    __tablename__ = "logauditoria"

    id = Column(Integer, Identity(), primary_key=True)
    administrador_id = Column(Integer, nullable=False)
    accion = Column(Text, nullable=False)
    fecha = Column("TIMESTAMP", Date, nullable=False)
    descripcion_cambio = Column(Text, nullable=True)
