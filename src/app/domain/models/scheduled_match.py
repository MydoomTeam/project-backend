from sqlalchemy import Column, Date, ForeignKey, Integer, Text
from sqlalchemy.schema import Identity

from app.core.database import Base


class ScheduledMatch(Base):
    __tablename__ = "scheduled_matches"

    id = Column(Integer, Identity(), primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)
    next_match_id = Column(Integer, nullable=True)
    match_status = Column(Text, nullable=False)
    score_detail = Column(Text, nullable=False)
    scheduled_datetime = Column(Date, nullable=False)
    result = Column(Text, nullable=True)
