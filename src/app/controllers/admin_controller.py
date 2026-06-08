from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_admin_id
from app.domain.schemas.admin import AdminPasswordUpdate
from app.repositories.admin_repository import AdminRepository
from app.repositories.audit_repository import AuditRepository
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admins", tags=["admins"])

def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    admin_repo = AdminRepository(db)
    audit_repo = AuditRepository(db)
    return AdminService(admin_repo, audit_repo)

@router.post("/password")
def update_admin_password(
    data: AdminPasswordUpdate,
    admin_id: int = Depends(get_current_admin_id),
    service: AdminService = Depends(get_admin_service)
):
    return service.update_password(admin_id, data)
