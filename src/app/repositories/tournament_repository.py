from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.domain.models.player import Player
from app.models.match import MatchModel
from app.models.registration import RegistrationModel
from app.models.tournament import TournamentModel


class TournamentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, torneo_id: int) -> TournamentModel | None:
        stmt = select(TournamentModel).where(TournamentModel.id == torneo_id)
        return self.db.execute(stmt).scalars().first()

    def get_active_by_name(self, nombre: str) -> TournamentModel | None:
        stmt = select(TournamentModel).where(
            TournamentModel.nombre == nombre,
            TournamentModel.estado != "Finalizado",
        )
        return self.db.execute(stmt).scalars().first()

    def list_available(self) -> list[TournamentModel]:
        stmt = select(TournamentModel).where(TournamentModel.estado == "Pendiente").order_by(TournamentModel.id.asc())
        return list(self.db.execute(stmt).scalars().all())

    def get_detail_with_creator(self, torneo_id: int) -> tuple[TournamentModel, str, int] | None:
        stmt = (
            select(TournamentModel, Player.nombre_usuario)
            .join(Player, Player.id == TournamentModel.creador_id)
            .where(TournamentModel.id == torneo_id)
        )
        row = self.db.execute(stmt).first()
        if row is None:
            return None
        tournament, creator_name = row
        count_stmt = (
            select(func.count())
            .select_from(RegistrationModel)
            .where(
                RegistrationModel.torneo_id == torneo_id,
                RegistrationModel.estado == "Confirmado",
            )
        )
        total = self.db.execute(count_stmt).scalar() or 0
        return tournament, creator_name, total

    def get_confirmed_participants(self, torneo_id: int) -> list[tuple[int, int]]:
        stmt = (
            select(RegistrationModel.jugador_id, Player.elo_global)
            .join(Player, Player.id == RegistrationModel.jugador_id)
            .where(
                RegistrationModel.torneo_id == torneo_id,
                RegistrationModel.estado == "Confirmado",
            )
            .order_by(Player.elo_global.desc())
        )
        rows = self.db.execute(stmt).all()
        return [(int(row.jugador_id), int(row.elo_global)) for row in rows]

    def update_status(self, tournament: TournamentModel, new_status: str) -> TournamentModel:
        tournament.estado = new_status
        self.db.flush()
        self.db.commit()
        self.db.refresh(tournament)
        return tournament

    def delete(self, tournament: TournamentModel) -> None:
        self.db.execute(delete(MatchModel).where(MatchModel.torneo_id == tournament.id))
        self.db.execute(delete(RegistrationModel).where(RegistrationModel.torneo_id == tournament.id))
        self.db.delete(tournament)
        self.db.commit()

    def save(self, tournament: TournamentModel) -> TournamentModel:
        self.db.add(tournament)
        self.db.flush()
        self.db.commit()
        self.db.refresh(tournament)
        return tournament
