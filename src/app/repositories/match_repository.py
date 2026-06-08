from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.match import MatchModel


class MatchRepository:
    def __init__(self, db: Session):
        self.db = db

    def insertar_en_lote(self, matches: list[MatchModel]) -> list[MatchModel]:
        self.db.add_all(matches)
        self.db.flush()
        for match in matches:
            self.db.refresh(match)
        return matches

    def obtener_por_torneo(self, torneo_id: int) -> list[MatchModel]:
        stmt = (
            select(MatchModel)
            .where(MatchModel.torneo_id == torneo_id)
            .order_by(MatchModel.ronda.asc(), MatchModel.id.asc())
        )
        return list(self.db.execute(stmt).scalars().all())
