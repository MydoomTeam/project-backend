from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MatchModel(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    bracket_type: Mapped[str] = mapped_column(Text, nullable=False, default="ganadores")
    player1_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    player2_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    next_match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"), nullable=True)
    score_player1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_player2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_datetime: Mapped[date | None] = mapped_column(Date, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="Pendiente")
