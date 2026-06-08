from datetime import date

from fastapi import HTTPException

from app.domain.models.torneo import Torneo
from app.domain.schemas.torneo import TorneoCreate
from app.repositories.audit_repository import AuditRepository
from app.repositories.torneo_repository import TorneoRepository


class TorneoService:
    def __init__(self, torneo_repo: TorneoRepository, audit_repo: AuditRepository):
        self.torneo_repo = torneo_repo
        self.audit_repo = audit_repo

    def create_torneo(self, admin_id: int, schema: TorneoCreate):
        if schema.participantes_max < 2:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "details": ["El número de participantes debe ser al menos 2"],
                },
            )
        if schema.duracion_ronda_min <= 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "details": ["La duración por ronda debe ser mayor a 0"],
                },
            )
        if schema.tipo_eliminacion not in ["simple", "doble", "liga"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "details": ["Tipo de eliminación no válido"],
                },
            )
        if not schema.nombre:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "validation_error",
                    "details": ["El nombre es obligatorio"],
                },
            )

        torneo = Torneo(
            administrador_id=admin_id,
            nombre=schema.nombre,
            tipo_eliminacion=schema.tipo_eliminacion,
            nombre_juego="General",
            categoria_juego="General",
            numero_participantes=schema.participantes_max,
            numero_rondas=1,
            duracion_ronda=schema.duracion_ronda_min,
            estado="Pendiente",
            fecha_inicio=date.today(),
        )
        try:
            created_torneo = self.torneo_repo.create(torneo)
            self.audit_repo.log_action(
                administrador_id=admin_id,
                accion="CREATE_TORNEO",
                descripcion_cambio="Torneo",
            )
        except Exception:
            self.audit_repo.log_action(
                administrador_id=admin_id,
                accion="CREATE_TORNEO_FAILED",
                descripcion_cambio="Torneo",
            )
            raise HTTPException(
                status_code=500,
                detail="Error al crear el torneo en la base de datos",
            )

        return {
            "id": created_torneo.id,
            "nombre": created_torneo.nombre,
            "estado": created_torneo.estado,
            "opciones_siguientes": ["agregar_participantes", "generar_bracket"],
        }

    def get_torneo(self, torneo_id: int):
        torneo = self.torneo_repo.get_by_id(torneo_id)
        if not torneo:
            raise HTTPException(status_code=404, detail="Torneo no encontrado")

        return {
            "id": torneo.id,
            "nombre": torneo.nombre,
            "estado": torneo.estado,
            "metadata": {
                "tipo_eliminacion": torneo.tipo_eliminacion,
                "duracion_ronda_min": torneo.duracion_ronda,
                "participantes_max": torneo.numero_participantes,
            },
        }
