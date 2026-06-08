from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLogModel
from app.models.tournament import TournamentModel


class TournamentRepository:
    def __init__(self, db: Session):
        self.db = db

    def obtener_por_id(self, torneo_id: int) -> TournamentModel | None:
        stmt = select(TournamentModel).where(TournamentModel.id == torneo_id)
        return self.db.execute(stmt).scalars().first()

    def obtener_por_nombre_activo(self, nombre: str) -> TournamentModel | None:
        stmt = select(TournamentModel).where(
            TournamentModel.nombre == nombre,
            TournamentModel.estado != "Finalizado",
        )
        return self.db.execute(stmt).scalars().first()

    def listar_disponibles(self) -> list[TournamentModel]:
        stmt = select(TournamentModel).where(TournamentModel.estado == "Pendiente").order_by(TournamentModel.id.asc())
        return list(self.db.execute(stmt).scalars().all())

    def guardar_con_auditoria(
        self,
        torneo: TournamentModel,
        accion: str,
        fecha: datetime,
        usuario_id: int,
    ) -> TournamentModel:
        self.db.add(torneo)
        self.db.flush()
        self.db.add(
            AuditLogModel(
                accion=accion,
                fecha=fecha,
                usuario_id=usuario_id,
            )
        )
        self.db.commit()
        self.db.refresh(torneo)
        return torneo
