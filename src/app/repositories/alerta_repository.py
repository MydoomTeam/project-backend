from datetime import date

from sqlalchemy.orm import Session

from app.domain.models.alerta import Alerta


class AlertaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[Alerta]:
        return self.db.query(Alerta).order_by(Alerta.fecha_hora.desc()).all()

    def get_by_id(self, alerta_id: int) -> Alerta | None:
        return self.db.query(Alerta).filter(Alerta.id == alerta_id).first()

    def create(self, tipo: str, mensaje: str) -> Alerta:
        existing = self.db.query(Alerta).filter(
            Alerta.tipo_evento == tipo,
            Alerta.mensaje == mensaje,
            Alerta.estado_lectura == "nueva",
        ).first()
        if existing:
            return existing

        alerta = Alerta(
            tipo_evento=tipo,
            mensaje=mensaje,
            fecha_hora=date.today(),
            estado_lectura="nueva",
        )
        self.db.add(alerta)
        self.db.commit()
        self.db.refresh(alerta)
        return alerta

    def acknowledge(self, alerta: Alerta) -> Alerta:
        alerta.estado_lectura = "reconocida"
        self.db.add(alerta)
        self.db.commit()
        self.db.refresh(alerta)
        return alerta
