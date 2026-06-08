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

    def obtener_por_id(self, match_id: int) -> MatchModel | None:
        return self.db.execute(
            select(MatchModel).where(MatchModel.id == match_id)
        ).scalars().first()

    def obtener_por_torneo(self, torneo_id: int) -> list[MatchModel]:
        stmt = (
            select(MatchModel)
            .where(MatchModel.torneo_id == torneo_id)
            .order_by(MatchModel.ronda.asc(), MatchModel.posicion.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def obtener_por_torneo_ronda(self, torneo_id: int, ronda: int) -> list[MatchModel]:
        stmt = (
            select(MatchModel)
            .where(MatchModel.torneo_id == torneo_id, MatchModel.ronda == ronda)
            .order_by(MatchModel.posicion.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def obtener_por_torneo_ronda_posicion(
        self, torneo_id: int, ronda: int, posicion: int
    ) -> MatchModel | None:
        stmt = select(MatchModel).where(
            MatchModel.torneo_id == torneo_id,
            MatchModel.ronda == ronda,
            MatchModel.posicion == posicion,
        )
        return self.db.execute(stmt).scalars().first()

    def obtener_byes_ronda1(self, torneo_id: int) -> list[MatchModel]:
        stmt = select(MatchModel).where(
            MatchModel.torneo_id == torneo_id,
            MatchModel.ronda == 1,
            MatchModel.jugador2_id.is_(None),
        ).order_by(MatchModel.posicion.asc())
        return list(self.db.execute(stmt).scalars().all())
