from sqlalchemy import Column, Date, Integer
from sqlalchemy.schema import Identity

from app.core.database import Base


class EloHistory(Base):
    __tablename__ = "elo_history"

    id = Column(Integer, Identity(), primary_key=True)
    match_id = Column(Integer, nullable=False)
    player_id = Column(Integer, nullable=False)
    previous_elo = Column(Integer, nullable=False)
    current_elo = Column(Integer, nullable=False)
    change_date = Column(Date, nullable=False)
