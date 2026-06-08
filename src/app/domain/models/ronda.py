from sqlalchemy import Column, Integer
from sqlalchemy.schema import Identity

from app.core.database import Base


class Ronda(Base):
    __tablename__ = "ronda"

    id = Column(Integer, Identity(), primary_key=True)
    torneo_id = Column(Integer, nullable=False)
    numero_fase = Column(Integer, nullable=False)
