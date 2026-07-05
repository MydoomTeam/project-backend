from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.engine import Result
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.domain.models.player import Player
from app.models.match import MatchModel
from app.models.registration import RegistrationModel
from app.models.tournament import TournamentModel


class TournamentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tournament_id: int) -> TournamentModel | None:
        stmt = select(TournamentModel).where(TournamentModel.id == tournament_id)
        return self.db.execute(stmt).scalars().first()

    def get_active_by_name(self, name: str) -> TournamentModel | None:
        stmt = select(TournamentModel).where(
            TournamentModel.name == name,
            TournamentModel.status != "Finalizado",
        )
        return self.db.execute(stmt).scalars().first()

    def _build_tournament_query(
        self,
        only_available: bool = False,
        include_creator: bool = False,
    ) -> Select[Any]:
        stmt: Select[Any] = select(TournamentModel)

        if include_creator:
            stmt = (
                select(TournamentModel, Player.username, Player.avatar_url)
                .join(Player, Player.id == TournamentModel.creator_id)
            )

        if only_available:
            stmt = stmt.where(TournamentModel.status == "Pendiente")

        return stmt

    def _execute_tournament_query(self, stmt: Select[Any]) -> list[tuple[Any, ...]]:
        result: Result[tuple[Any, ...]] = self.db.execute(stmt)
        return [tuple(row) for row in result.all()]

    def list_available(self) -> list[TournamentModel]:
        stmt = self._build_tournament_query(only_available=True)
        return list(self.db.execute(stmt).scalars().all())

    def list_all(self) -> list[TournamentModel]:
        stmt = self._build_tournament_query()
        return list(self.db.execute(stmt).scalars().all())

    def list_available_with_creator(self) -> list[tuple[TournamentModel, str | None, str | None]]:
        stmt = self._build_tournament_query(only_available=True, include_creator=True)
        result: Result[tuple[TournamentModel, str | None, str | None]] = self.db.execute(stmt)
        return [(row[0], row[1], row[2]) for row in result.all()]

    def list_all_with_creator(self) -> list[tuple[TournamentModel, str | None, str | None]]:
        stmt = self._build_tournament_query(include_creator=True)
        result: Result[tuple[TournamentModel, str | None, str | None]] = self.db.execute(stmt)
        return [(row[0], row[1], row[2]) for row in result.all()]

    @staticmethod
    def _detail_with_creator_stmt(tournament_id: int) -> Select[Any]:
        return (
            select(TournamentModel, Player.username, Player.avatar_url)
            .join(Player, Player.id == TournamentModel.creator_id)
            .where(TournamentModel.id == tournament_id)
        )

    def _confirmed_participants_total(self, tournament_id: int) -> int:
        count_stmt = (
            select(func.count(RegistrationModel.id))
            .select_from(RegistrationModel)
            .where(
                RegistrationModel.tournament_id == tournament_id,
                RegistrationModel.status == "Confirmado",
            )
        )
        return self.db.execute(count_stmt).scalar() or 0

    @staticmethod
    def _detail_tuple(
        row: tuple[TournamentModel, str, str | None],
        total: int,
    ) -> tuple[TournamentModel, str, str | None, int]:
        tournament, creator_name, creator_avatar_url = row
        return tournament, creator_name, creator_avatar_url, total

    def get_detail_with_creator(self, tournament_id: int) -> tuple[TournamentModel, str, str | None, int] | None:
        row = self.db.execute(self._detail_with_creator_stmt(tournament_id)).first()
        if row is None:
            return None
        return self._detail_tuple(row, self._confirmed_participants_total(tournament_id))

    @staticmethod
    def _player_tournament_history_stmt(player_id: int) -> Select[Any]:
        return (
            select(TournamentModel, RegistrationModel.status)
            .outerjoin(
                RegistrationModel,
                (RegistrationModel.tournament_id == TournamentModel.id)
                & (RegistrationModel.player_id == player_id),
            )
            .where(
                or_(
                    TournamentModel.creator_id == player_id,
                    RegistrationModel.player_id == player_id,
                )
            )
            .order_by(TournamentModel.id.desc())
        )

    def get_confirmed_participants(self, tournament_id: int) -> list[tuple[int, int]]:
        stmt = (
            select(RegistrationModel.player_id, Player.global_elo)
            .join(Player, Player.id == RegistrationModel.player_id)
            .where(
                RegistrationModel.tournament_id == tournament_id,
                RegistrationModel.status == "Confirmado",
            )
            .order_by(Player.global_elo.desc())
        )
        rows = self.db.execute(stmt).all()
        return [(int(row[0]), int(row[1])) for row in rows]

    def update_status(self, tournament: TournamentModel, new_status: str) -> TournamentModel:
        tournament.status = new_status
        self.db.flush()
        self.db.commit()
        self.db.refresh(tournament)
        return tournament

    def delete(self, tournament: TournamentModel) -> None:
        self.db.execute(delete(MatchModel).where(MatchModel.tournament_id == tournament.id))
        self.db.execute(delete(RegistrationModel).where(RegistrationModel.tournament_id == tournament.id))
        self.db.delete(tournament)
        self.db.commit()

    def save(self, tournament: TournamentModel) -> TournamentModel:
        self.db.add(tournament)
        self.db.flush()
        self.db.commit()
        self.db.refresh(tournament)
        return tournament

    def list_player_tournament_history(
        self,
        player_id: int,
    ) -> list[tuple[TournamentModel, str | None]]:
        rows = self.db.execute(self._player_tournament_history_stmt(player_id)).all()
        return [(row[0], row[1]) for row in rows]
