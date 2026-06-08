from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.tournament import TournamentModel
from app.repositories.tournament_repository import TournamentRepository
from app.schemas.tournament import TournamentCreate, TournamentDetailResponse


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

    def crear_torneo(self, data: TournamentCreate, creador_id: int) -> TournamentModel:
        if data.tipo_eliminacion == "Eliminación Sencilla" and data.rondas > 7:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El número de rondas no es congruente con Eliminación Sencilla",
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
