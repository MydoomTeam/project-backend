from sqlalchemy.orm import Session

from app.domain.models.torneo import Torneo


class TorneoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, torneo_id: int) -> Torneo | None:
        return self.db.query(Torneo).filter(Torneo.id == torneo_id).first()

    def create(self, torneo: Torneo) -> Torneo:
        self.db.add(torneo)
        self.db.commit()
        self.db.refresh(torneo)
        return torneo
