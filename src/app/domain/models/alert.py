from sqlalchemy import Column, Date, Integer, Text
from sqlalchemy.schema import Identity

from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, Identity(), primary_key=True)
    admin_id = Column(Integer, nullable=True)
    player_id = Column(Integer, nullable=True)
    event_type = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    datetime = Column(Date, nullable=False)
    read_status = Column(Text, nullable=False)
