from datetime import date

from sqlalchemy.orm import Session

from app.domain.models.elo_history import EloHistory


class EloHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        player_id: int,
        match_id: int,
        previous_elo: int,
        current_elo: int,
    ) -> None:
        entry = EloHistory(
            player_id=player_id,
            match_id=match_id,
            previous_elo=previous_elo,
            current_elo=current_elo,
            change_date=date.today(),
        )
        self.db.add(entry)

    def get_by_player(self, player_id: int) -> list[EloHistory]:
        return (
            self.db.query(EloHistory)
            .filter(EloHistory.player_id == player_id)
            .order_by(EloHistory.change_date.desc(), EloHistory.id.desc())
            .all()
        )
