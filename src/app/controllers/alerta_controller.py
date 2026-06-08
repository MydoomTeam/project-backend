from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin_id
from app.domain.schemas.alerta import AckResponse, AlertaListResponse
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.audit_repository import AuditRepository
from app.services.alerta_service import AlertaService

router = APIRouter(prefix="/alerts", tags=["alerts"])


def get_alerta_service(db: Session = Depends(get_db)) -> AlertaService:
    alerta_repo = AlertaRepository(db)
    audit_repo = AuditRepository(db)
    return AlertaService(alerta_repo, audit_repo)


@router.get("", response_model=AlertaListResponse)
def get_alertas(
    _admin_id: int = Depends(get_current_admin_id),
    service: AlertaService = Depends(get_alerta_service),
):
    return {"items": service.get_alertas()}

@router.patch("/{id}/ack", response_model=AckResponse)
def acknowledge_alerta(
    id: int,
    admin_id: int = Depends(get_current_admin_id),
    service: AlertaService = Depends(get_alerta_service)
):
    return service.acknowledge_alerta(admin_id, id)
