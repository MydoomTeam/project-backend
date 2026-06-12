from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.domain.schemas.alerta import AckResponse, AlertaListResponse
from app.services.alerta_service import AlertaService

router = APIRouter(prefix="/alerts", tags=["alerts"])


def get_alerta_service(db: Session = Depends(get_db)) -> AlertaService:
    return AlertaService.from_session(db)


@router.get("", response_model=AlertaListResponse)
def get_alerts(
    _jugador_id: int = Depends(get_current_user),
    service: AlertaService = Depends(get_alerta_service),
):
    return {"items": service.get_alerts()}

@router.patch("/{id}/ack", response_model=AckResponse)
def acknowledge_alert(
    id: int,
    jugador_id: int = Depends(get_current_user),
    service: AlertaService = Depends(get_alerta_service)
):
    return service.acknowledge_alert(jugador_id, id)
