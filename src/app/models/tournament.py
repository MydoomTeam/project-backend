from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TournamentModel(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    elimination_type: Mapped[str] = mapped_column(Text, nullable=False)
    game_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    game_category: Mapped[str | None] = mapped_column(Text, nullable=True)
    participant_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rounds: Mapped[int] = mapped_column(Integer, nullable=False)
    round_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uses_score: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="Pendiente")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    language: Mapped[str | None] = mapped_column(Text, nullable=True)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
