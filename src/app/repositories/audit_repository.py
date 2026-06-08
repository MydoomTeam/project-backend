from datetime import date

from sqlalchemy.orm import Session

from app.domain.models.log_auditoria import LogAuditoria


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def log_action(
        self,
        administrador_id: int,
        accion: str,
        descripcion_cambio: str | None = None,
    ) -> LogAuditoria:
        log = LogAuditoria(
            administrador_id=administrador_id,
            accion=accion,
            timestamp=date.today(),
            descripcion_cambio=descripcion_cambio,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
