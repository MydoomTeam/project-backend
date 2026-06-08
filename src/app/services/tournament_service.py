from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.tournament import TournamentModel
from app.repositories.tournament_repository import TournamentRepository
from app.schemas.tournament import TournamentCreate


class TournamentService:
    def __init__(self, db: Session):
        self.repo = TournamentRepository(db)

    def obtener_torneos_disponibles(self) -> list[TournamentModel]:
        return self.repo.listar_disponibles()

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
