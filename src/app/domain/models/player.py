from sqlalchemy import Column, Date, Integer, Text
from sqlalchemy.schema import Identity

from app.core.database import Base


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, Identity(), primary_key=True)
    username = Column(Text, nullable=False)
    email = Column(Text, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    last_access_date = Column(Date, nullable=False)
    global_elo = Column(Integer, nullable=False)
    avatar_url = Column(Text, nullable=True)
