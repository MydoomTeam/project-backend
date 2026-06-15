from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.models.alert import Alert


class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[Alert]:
        return self.db.query(Alert).order_by(Alert.created_at.desc()).all()

    def get_by_id(self, alert_id: int) -> Alert | None:
        return self.db.query(Alert).filter(Alert.id == alert_id).first()

    def create(self, event_type: str, message: str) -> Alert:
        existing = self.db.query(Alert).filter(
            Alert.event_type == event_type,
            Alert.message == message,
        ).first()
        if existing:
            return existing

        alert = Alert(
            event_type=event_type,
            message=message,
            created_at=datetime.now(),
            read_status="nueva",
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def acknowledge(self, alert: Alert) -> Alert:
        alert.read_status = "reconocida"
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
