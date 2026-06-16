from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domain.schemas.alert import AlertActivityResponse, AlertResponse
from app.repositories.alert_repository import AlertRepository
from app.repositories.audit_log_repository import AuditLogRepository


class AlertService:
    def __init__(self, alert_repo: AlertRepository, audit_repo: AuditLogRepository):
        self.alert_repo = alert_repo
        self.audit_repo = audit_repo

    @classmethod
    def from_session(cls, db: Session) -> "AlertService":
        return cls(AlertRepository(db), AuditLogRepository(db))

    def get_alerts(self) -> dict:
        alerts = [self._to_response(alert) for alert in self.alert_repo.get_all()]
        history = [
            self._to_activity(log)
            for log in self.audit_repo.list_recent()
            if log.action != "CHECK_OVERDUE_OK"
        ]
        return {
            "items": alerts,
            "stats": {
                "total": len(alerts),
                "new": sum(1 for alert in alerts if alert.status == "nueva"),
                "acknowledged": sum(1 for alert in alerts if alert.status == "reconocida"),
                "critical": sum(1 for alert in alerts if alert.event_type == "match_overdue" and alert.status == "nueva"),
            },
            "history": history,
        }

    def acknowledge_alert(self, actor_id: int, alert_id: int):
        alert = self.alert_repo.get_by_id(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        self.alert_repo.acknowledge(alert)
        self.audit_repo.log_action(
            actor_id=actor_id,
            action="ACK_ALERTA",
            change_description=f"Alert:{alert_id}",
        )
        return {"message": "acknowledged"}

    @staticmethod
    def _to_response(alert) -> AlertResponse:
        return AlertResponse(
            id=alert.id,
            event_type=alert.event_type,
            message=alert.message,
            created_at=alert.created_at,
            status=alert.read_status,
        )

    @staticmethod
    def _to_activity(log) -> AlertActivityResponse:
        return AlertActivityResponse(
            id=log.id,
            action=log.action,
            created_at=log.created_at,
            description=log.change_description,
        )
