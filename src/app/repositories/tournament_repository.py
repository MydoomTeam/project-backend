from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

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

    def list_available(self) -> list[TournamentModel]:
        stmt = select(TournamentModel).where(TournamentModel.status == "Pendiente").order_by(TournamentModel.id.asc())
        return list(self.db.execute(stmt).scalars().all())

    def get_detail_with_creator(self, tournament_id: int) -> tuple[TournamentModel, str, int] | None:
        stmt = (
            select(TournamentModel, Player.username)
            .join(Player, Player.id == TournamentModel.creator_id)
            .where(TournamentModel.id == tournament_id)
        )
        row = self.db.execute(stmt).first()
        if row is None:
            return None
        tournament, creator_name = row
        count_stmt = (
            select(func.count())
            .select_from(RegistrationModel)
            .where(
                RegistrationModel.tournament_id == tournament_id,
                RegistrationModel.status == "Confirmado",
            )
        )
        total = self.db.execute(count_stmt).scalar() or 0
        return tournament, creator_name, total

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
        return [(int(row.player_id), int(row.global_elo)) for row in rows]

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
