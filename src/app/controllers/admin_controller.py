from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_admin_id
from app.domain.schemas.admin import AdminPasswordUpdate
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admins", tags=["admins"])

def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    return AdminService.from_session(db)

@router.post("/password")
def update_admin_password(
    data: AdminPasswordUpdate,
    admin_id: int = Depends(get_current_admin_id),
    service: AdminService = Depends(get_admin_service)
):
    return service.update_password(admin_id, data)
