from datetime import date

from sqlalchemy.orm import Session

from app.domain.models.alert import Alert


class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[Alert]:
        return self.db.query(Alert).order_by(Alert.fecha_hora.desc()).all()

    def get_by_id(self, alert_id: int) -> Alert | None:
        return self.db.query(Alert).filter(Alert.id == alert_id).first()

    def create(self, tipo: str, mensaje: str) -> Alert:
        existing = self.db.query(Alert).filter(
            Alert.tipo_evento == tipo,
            Alert.mensaje == mensaje,
            Alert.estado_lectura == "nueva",
        ).first()
        if existing:
            return existing

        alert = Alert(
            tipo_evento=tipo,
            mensaje=mensaje,
            fecha_hora=date.today(),
            estado_lectura="nueva",
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def acknowledge(self, alert: Alert) -> Alert:
        alert.estado_lectura = "reconocida"
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
