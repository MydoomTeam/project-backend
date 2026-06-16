from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.domain.schemas.alert import AckResponse, AlertListResponse
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


def get_alert_service(db: Session = Depends(get_db)) -> AlertService:
    return AlertService.from_session(db)


@router.get("", response_model=AlertListResponse)
def get_alerts(
    _player_id: int = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    return service.get_alerts()

@router.patch("/{alert_id}/ack", response_model=AckResponse)
def acknowledge_alert(
    alert_id: int,
    player_id: int = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service)
):
    return service.acknowledge_alert(player_id, alert_id)
