from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.tournament import TournamentModel
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.tournament_repository import TournamentRepository
from app.schemas.tournament import TournamentCreate, TournamentDetailResponse

_MAX_ROUNDS_BY_FORMAT: dict[str, int] = {
    "Eliminación Sencilla": 7,
    "Eliminación Doble":    5,
    "Round Robin":          3,
    "Swiss":                7,
}


class TournamentService:
    def __init__(self, db: Session):
        self.repo = TournamentRepository(db)
        self.audit_repo = AuditLogRepository(db)

    def get_available_tournaments(self) -> list[TournamentModel]:
        return self.repo.list_available()

    def get_tournament_detail(self, torneo_id: int) -> TournamentDetailResponse:
        result = self.repo.get_detail_with_creator(torneo_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Torneo no encontrado",
            )
        tournament, creator_name, total_participants = result
        return TournamentDetailResponse(
            id=tournament.id,
            nombre=tournament.nombre,
            tipo_eliminacion=tournament.tipo_eliminacion,
            rondas=tournament.rondas,
            estado=tournament.estado,
            creador_id=tournament.creador_id,
            creador_nombre=creator_name,
            total_participantes=total_participants,
        )

    def cancel_tournament(self, torneo_id: int, admin_id: int) -> None:
        tournament = self.repo.get_by_id(torneo_id)
        if tournament is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Torneo no encontrado",
            )
        if tournament.creador_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede cancelar el torneo",
            )
        if tournament.estado not in ("Pendiente", "Listo para iniciar"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede cancelar un torneo en estado Pendiente o Listo para iniciar",
            )
        self.audit_repo.record(accion="CANCELAR_TORNEO", usuario_id=admin_id, fecha=datetime.now())
        self.repo.delete(tournament)

    def create_tournament(self, data: TournamentCreate, creador_id: int) -> TournamentModel:
        max_rounds = _MAX_ROUNDS_BY_FORMAT.get(data.tipo_eliminacion)
        if max_rounds is None:
            formats = list(_MAX_ROUNDS_BY_FORMAT)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato '{data.tipo_eliminacion}' no reconocido. Válidos: {formats}",
            )
        if data.rondas > max_rounds:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{data.tipo_eliminacion}' admite máximo {max_rounds} rondas",
            )

        existing = self.repo.get_active_by_name(data.nombre)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un torneo activo con ese nombre",
            )

        tournament = TournamentModel(
            nombre=data.nombre,
            tipo_eliminacion=data.tipo_eliminacion,
            rondas=data.rondas,
            estado="Pendiente",
            creador_id=creador_id,
        )
        self.audit_repo.record(accion="CREAR_TORNEO", usuario_id=creador_id, fecha=datetime.now())
        return self.repo.save(tournament)
