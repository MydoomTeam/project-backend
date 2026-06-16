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
        action: str,
        user_id: int,
        created_at: datetime,
        change_description: str | None = None,
    ) -> None:
        self.db.add(
            AuditLogModel(
                action=action,
                created_at=created_at,
                user_id=user_id,
                change_description=change_description,
            )
        )

    def log_action(
        self,
        actor_id: int,
        action: str,
        change_description: str | None = None,
    ) -> None:
        self.record(
            action=action,
            user_id=actor_id,
            created_at=datetime.now(),
            change_description=change_description,
        )
        self.db.commit()

    def list_recent(self, limit: int = 12) -> list[AuditLogModel]:
        return (
            self.db.query(AuditLogModel)
            .order_by(AuditLogModel.created_at.desc(), AuditLogModel.id.desc())
            .limit(limit)
            .all()
        )
