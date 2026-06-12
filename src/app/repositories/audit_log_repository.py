from datetime import datetime

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLogModel


class AuditLogRepository:
    """Único punto de escritura de la tabla audit_logs (fuente de verdad de auditoría).

    `record` agrega el registro a la sesión activa SIN commit, para que el caller
    controle la frontera transaccional (flujos de torneos/partidas).
    `log_action` agrega y hace commit inmediato, para auditorías independientes de
    una transacción mayor (cambio de password, alertas, scheduler).
    """

    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        accion: str,
        usuario_id: int,
        fecha: datetime,
        descripcion_cambio: str | None = None,
    ) -> None:
        self.db.add(
            AuditLogModel(
                accion=accion,
                fecha=fecha,
                usuario_id=usuario_id,
                descripcion_cambio=descripcion_cambio,
            )
        )

    def log_action(
        self,
        actor_id: int,
        accion: str,
        descripcion_cambio: str | None = None,
    ) -> None:
        self.record(
            accion=accion,
            usuario_id=actor_id,
            fecha=datetime.now(),
            descripcion_cambio=descripcion_cambio,
        )
        self.db.commit()
