from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_admin_id
from app.domain.schemas.torneo import TorneoCreate, TorneoResponse, TorneoDetailResponse
from app.repositories.torneo_repository import TorneoRepository
from app.repositories.audit_repository import AuditRepository
from app.services.torneo_service import TorneoService

router = APIRouter(prefix="/tournaments", tags=["tournaments"])

def get_torneo_service(db: Session = Depends(get_db)) -> TorneoService:
    torneo_repo = TorneoRepository(db)
    audit_repo = AuditRepository(db)
    return TorneoService(torneo_repo, audit_repo)

@router.post("", response_model=TorneoResponse, status_code=201)
def create_torneo(
    data: TorneoCreate,
    admin_id: int = Depends(get_current_admin_id),
    service: TorneoService = Depends(get_torneo_service)
):
    return service.create_torneo(admin_id, data)

@router.get("/{torneo_id}", response_model=TorneoDetailResponse)
def get_torneo(
    torneo_id: int,
    service: TorneoService = Depends(get_torneo_service)
):
    return service.get_torneo(torneo_id)
