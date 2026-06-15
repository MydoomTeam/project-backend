from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text
from sqlalchemy.schema import Identity

from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, Identity(), primary_key=True)
    admin_id = Column(Integer, nullable=True)
    player_id = Column(Integer, nullable=True)
    event_type = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    read_status = Column(Text, nullable=False)
