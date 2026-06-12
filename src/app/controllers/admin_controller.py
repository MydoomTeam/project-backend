from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.domain.schemas.jugador import PasswordUpdate
from app.services.jugador_service import JugadorService

router = APIRouter(prefix="/admins", tags=["admins"])


@router.post("/password")
def update_admin_password(
    data: PasswordUpdate,
    jugador_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JugadorService(db).cambiar_password(jugador_id, data)
