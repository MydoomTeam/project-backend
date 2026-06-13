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

    def insert_batch(self, matches: list[MatchModel]) -> list[MatchModel]:
        self.db.add_all(matches)
        self.db.flush()
        for match in matches:
            self.db.refresh(match)
        return matches

    def get_by_id(self, match_id: int) -> MatchModel | None:
        return self.db.execute(
            select(MatchModel).where(MatchModel.id == match_id)
        ).scalars().first()

    def get_by_tournament(self, tournament_id: int) -> list[MatchModel]:
        stmt = (
            select(MatchModel)
            .where(MatchModel.tournament_id == tournament_id)
            .order_by(MatchModel.round.asc(), MatchModel.position.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_tournament_round(self, tournament_id: int, round: int) -> list[MatchModel]:
        stmt = (
            select(MatchModel)
            .where(MatchModel.tournament_id == tournament_id, MatchModel.round == round)
            .order_by(MatchModel.position.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_tournament_round_position(
        self, tournament_id: int, round: int, position: int
    ) -> MatchModel | None:
        stmt = select(MatchModel).where(
            MatchModel.tournament_id == tournament_id,
            MatchModel.round == round,
            MatchModel.position == position,
        )
        return self.db.execute(stmt).scalars().first()

    def get_by_tournament_round_position_bracket(
        self, tournament_id: int, round: int, position: int, bracket_type: str
    ) -> MatchModel | None:
        stmt = select(MatchModel).where(
            MatchModel.tournament_id == tournament_id,
            MatchModel.round == round,
            MatchModel.position == position,
            MatchModel.bracket_type == bracket_type,
        )
        return self.db.execute(stmt).scalars().first()

    def get_round1_byes(self, tournament_id: int) -> list[MatchModel]:
        stmt = (
            select(MatchModel)
            .where(
                MatchModel.tournament_id == tournament_id,
                MatchModel.round == 1,
                MatchModel.bracket_type == "ganadores",
                MatchModel.player1_id.is_not(None),
                MatchModel.player2_id.is_(None),
            )
            .order_by(MatchModel.position.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_active_by_tournament(self, tournament_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(MatchModel)
            .where(
                MatchModel.tournament_id == tournament_id,
                MatchModel.status != "Finalizado",
            )
        )
        return self.db.execute(stmt).scalar() or 0

    def count_active_by_round(self, tournament_id: int, round: int) -> int:
        stmt = (
            select(func.count())
            .select_from(MatchModel)
            .where(
                MatchModel.tournament_id == tournament_id,
                MatchModel.round == round,
                MatchModel.status != "Finalizado",
            )
        )
        return self.db.execute(stmt).scalar() or 0

    def get_max_round(self, tournament_id: int) -> int:
        stmt = (
            select(func.max(MatchModel.round))
            .where(MatchModel.tournament_id == tournament_id)
        )
        return self.db.execute(stmt).scalar() or 0

    def get_wins_by_player(self, tournament_id: int) -> dict[int, int]:
        stmt = (
            select(MatchModel.winner_id, func.count())
            .where(
                MatchModel.tournament_id == tournament_id,
                MatchModel.winner_id.is_not(None),
            )
            .group_by(MatchModel.winner_id)
        )
        rows = self.db.execute(stmt).all()
        return {jugador_id: count for jugador_id, count in rows}

    def get_player_history(self, tournament_id: int, jugador_id: int) -> list[MatchModel]:
        stmt = (
            select(MatchModel)
            .where(
                MatchModel.tournament_id == tournament_id,
                or_(
                    MatchModel.player1_id == jugador_id,
                    MatchModel.player2_id == jugador_id,
                ),
                MatchModel.player1_id.is_not(None),
                MatchModel.player2_id.is_not(None),
            )
            .order_by(MatchModel.round.asc(), MatchModel.position.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_played_pairs(self, tournament_id: int) -> set[tuple[int, int]]:
        stmt = select(MatchModel.player1_id, MatchModel.player2_id).where(
            MatchModel.tournament_id == tournament_id,
            MatchModel.player1_id.is_not(None),
            MatchModel.player2_id.is_not(None),
        )
        rows = self.db.execute(stmt).all()
        return {(min(j1, j2), max(j1, j2)) for j1, j2 in rows}
