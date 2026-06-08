from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import resolve_user_id
from app.core.database import get_db
from app.schemas.tournament import TournamentCreate, TournamentResponse
from app.services.tournament_service import TournamentService

router = APIRouter(tags=["tournaments"])


def get_current_user_id(authorization: str | None = Header(default=None, alias="Authorization")) -> int:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no autenticado",
        )
    token = authorization.removeprefix("Bearer ").strip()
    user_id = resolve_user_id(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no autenticado",
        )
    return user_id


@router.post("/tournaments", response_model=TournamentResponse, status_code=status.HTTP_201_CREATED)
def crear_torneo(
    payload: TournamentCreate,
    db: Session = Depends(get_db),
    creador_id: int = Depends(get_current_user_id),
) -> TournamentResponse:
    service = TournamentService(db)
    return service.crear_torneo(payload, creador_id)
