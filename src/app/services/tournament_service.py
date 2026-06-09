from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.tournament import TournamentModel
from app.repositories.tournament_repository import TournamentRepository
from app.schemas.tournament import TournamentCreate, TournamentDetailResponse

_MAX_RONDAS_POR_FORMATO: dict[str, int] = {
    "Eliminación Sencilla": 7,
    "Eliminación Doble":    5,
    "Round Robin":          3,
    "Swiss":                7,
}

_MIN_PARTICIPANTES_POR_FORMATO: dict[str, int] = {
    "Eliminación Sencilla": 2,
    "Eliminación Doble":    4,
    "Round Robin":          3,
    "Swiss":                4,
}


class TournamentService:
    def __init__(self, db: Session):
        self.repo = TournamentRepository(db)

    def obtener_torneos_disponibles(self) -> list[TournamentModel]:
        return self.repo.listar_disponibles()

    def obtener_detalle_torneo(self, torneo_id: int) -> TournamentDetailResponse:
        resultado = self.repo.obtener_detalle_con_creador(torneo_id)
        if resultado is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Torneo no encontrado",
            )
        torneo, creador_nombre, total_participantes = resultado
        return TournamentDetailResponse(
            id=torneo.id,
            nombre=torneo.nombre,
            tipo_eliminacion=torneo.tipo_eliminacion,
            rondas=torneo.rondas,
            estado=torneo.estado,
            creador_id=torneo.creador_id,
            creador_nombre=creador_nombre,
            total_participantes=total_participantes,
        )

    def cancelar_torneo(self, torneo_id: int, admin_id: int) -> None:
        torneo = self.repo.obtener_por_id(torneo_id)
        if torneo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Torneo no encontrado",
            )
        if torneo.creador_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede cancelar el torneo",
            )
        if torneo.estado not in ("Pendiente", "Listo para iniciar"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede cancelar un torneo en estado Pendiente o Listo para iniciar",
            )
        self.repo.eliminar(
            torneo=torneo,
            accion="CANCELAR_TORNEO",
            fecha=datetime.now(),
            usuario_id=admin_id,
        )

    def crear_torneo(self, data: TournamentCreate, creador_id: int) -> TournamentModel:
        max_rondas = _MAX_RONDAS_POR_FORMATO.get(data.tipo_eliminacion)
        if max_rondas is None:
            formatos = list(_MAX_RONDAS_POR_FORMATO)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato '{data.tipo_eliminacion}' no reconocido. Válidos: {formatos}",
            )
        if data.rondas > max_rondas:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{data.tipo_eliminacion}' admite máximo {max_rondas} rondas",
            )

        existente = self.repo.obtener_por_nombre_activo(data.nombre)
        if existente is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un torneo activo con ese nombre",
            )

        torneo = TournamentModel(
            nombre=data.nombre,
            tipo_eliminacion=data.tipo_eliminacion,
            rondas=data.rondas,
            estado="Pendiente",
            creador_id=creador_id,
        )
        return self.repo.guardar_con_auditoria(
            torneo=torneo,
            accion="CREAR_TORNEO",
            fecha=datetime.now(),
            usuario_id=creador_id,
        )
