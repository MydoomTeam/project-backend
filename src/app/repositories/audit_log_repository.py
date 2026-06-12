from datetime import datetime

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLogModel


class AuditLogRepository:
    """Único punto de escritura de la tabla audit_logs (stack de torneos).

    No hace commit: agrega el registro a la sesión activa para que el caller
    controle la frontera transaccional.
    """

    def __init__(self, db: Session):
        self.db = db

    def record(self, accion: str, usuario_id: int, fecha: datetime) -> None:
        self.db.add(AuditLogModel(accion=accion, fecha=fecha, usuario_id=usuario_id))
