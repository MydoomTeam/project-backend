from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.match import MatchModel


class MatchRepository:
    def __init__(self, db: Session):
        self.db = db

    def flush(self) -> None:
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, entity: MatchModel) -> None:
        self.db.refresh(entity)

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

    def obtener_por_torneo_ronda_posicion_bracket(
        self, torneo_id: int, ronda: int, posicion: int, bracket_tipo: str
    ) -> MatchModel | None:
        stmt = select(MatchModel).where(
            MatchModel.torneo_id == torneo_id,
            MatchModel.ronda == ronda,
            MatchModel.posicion == posicion,
            MatchModel.bracket_tipo == bracket_tipo,
        )
        return self.db.execute(stmt).scalars().first()

    def obtener_byes_ronda1(self, torneo_id: int) -> list[MatchModel]:
        stmt = (
            select(MatchModel)
            .where(
                MatchModel.torneo_id == torneo_id,
                MatchModel.ronda == 1,
                MatchModel.bracket_tipo == "ganadores",
                MatchModel.jugador1_id.is_not(None),
                MatchModel.jugador2_id.is_(None),
            )
            .order_by(MatchModel.posicion.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def contar_activos_por_torneo(self, torneo_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(MatchModel)
            .where(
                MatchModel.torneo_id == torneo_id,
                MatchModel.estado != "Finalizado",
            )
        )
        return self.db.execute(stmt).scalar() or 0

    def contar_activos_por_ronda(self, torneo_id: int, ronda: int) -> int:
        stmt = (
            select(func.count())
            .select_from(MatchModel)
            .where(
                MatchModel.torneo_id == torneo_id,
                MatchModel.ronda == ronda,
                MatchModel.estado != "Finalizado",
            )
        )
        return self.db.execute(stmt).scalar() or 0

    def obtener_max_ronda(self, torneo_id: int) -> int:
        stmt = (
            select(func.max(MatchModel.ronda))
            .where(MatchModel.torneo_id == torneo_id)
        )
        return self.db.execute(stmt).scalar() or 0

    def obtener_victorias_por_jugador(self, torneo_id: int) -> dict[int, int]:
        stmt = (
            select(MatchModel.ganador_id, func.count())
            .where(
                MatchModel.torneo_id == torneo_id,
                MatchModel.ganador_id.is_not(None),
            )
            .group_by(MatchModel.ganador_id)
        )
        rows = self.db.execute(stmt).all()
        return {jugador_id: count for jugador_id, count in rows}

    def obtener_historial_jugador(self, torneo_id: int, jugador_id: int) -> list[MatchModel]:
        stmt = (
            select(MatchModel)
            .where(
                MatchModel.torneo_id == torneo_id,
                or_(
                    MatchModel.jugador1_id == jugador_id,
                    MatchModel.jugador2_id == jugador_id,
                ),
                MatchModel.jugador1_id.is_not(None),
                MatchModel.jugador2_id.is_not(None),
            )
            .order_by(MatchModel.ronda.asc(), MatchModel.posicion.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def obtener_pares_jugados(self, torneo_id: int) -> set[tuple[int, int]]:
        stmt = select(MatchModel.jugador1_id, MatchModel.jugador2_id).where(
            MatchModel.torneo_id == torneo_id,
            MatchModel.jugador1_id.is_not(None),
            MatchModel.jugador2_id.is_not(None),
        )
        rows = self.db.execute(stmt).all()
        return {(min(j1, j2), max(j1, j2)) for j1, j2 in rows}
