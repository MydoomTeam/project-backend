from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domain.schemas.alerta import AlertResponse
from app.repositories.alert_repository import AlertRepository
from app.repositories.audit_log_repository import AuditLogRepository


class AlertService:
    def __init__(self, alerta_repo: AlertRepository, audit_repo: AuditLogRepository):
        self.alerta_repo = alerta_repo
        self.audit_repo = audit_repo

    @classmethod
    def from_session(cls, db: Session) -> "AlertService":
        return cls(AlertRepository(db), AuditLogRepository(db))

    def get_alerts(self) -> list[AlertResponse]:
        return [self._to_response(alerta) for alerta in self.alerta_repo.get_all()]

    def acknowledge_alert(self, actor_id: int, alerta_id: int):
        alerta = self.alerta_repo.get_by_id(alerta_id)
        if not alerta:
            raise HTTPException(status_code=404, detail="Alert no encontrada")

        self.alerta_repo.acknowledge(alerta)
        self.audit_repo.log_action(
            actor_id=actor_id,
            accion="ACK_ALERTA",
            descripcion_cambio=f"Alert:{alerta_id}",
        )
        return {"message": "acknowledged"}

    @staticmethod
    def _to_response(alerta) -> AlertResponse:
        return AlertResponse(
            id=alerta.id,
            tipo=alerta.tipo_evento,
            mensaje=alerta.mensaje,
            created_at=alerta.fecha_hora,
            status=alerta.estado_lectura,
        )
