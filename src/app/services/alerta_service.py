from fastapi import HTTPException

from app.domain.schemas.alerta import AlertaResponse
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.audit_repository import AuditRepository


class AlertaService:
    def __init__(self, alerta_repo: AlertaRepository, audit_repo: AuditRepository):
        self.alerta_repo = alerta_repo
        self.audit_repo = audit_repo

    def get_alertas(self) -> list[AlertaResponse]:
        return [self._to_response(alerta) for alerta in self.alerta_repo.get_all()]

    def acknowledge_alerta(self, admin_id: int, alerta_id: int):
        alerta = self.alerta_repo.get_by_id(alerta_id)
        if not alerta:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        self.alerta_repo.acknowledge(alerta)
        self.audit_repo.log_action(
            administrador_id=admin_id,
            accion="ACK_ALERTA",
            descripcion_cambio=f"Alerta:{alerta_id}",
        )
        return {"message": "acknowledged"}

    @staticmethod
    def _to_response(alerta) -> AlertaResponse:
        return AlertaResponse(
            id=alerta.id,
            tipo=alerta.tipo_evento,
            mensaje=alerta.mensaje,
            created_at=alerta.fecha_hora,
            status=alerta.estado_lectura,
        )
