from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.schemas.registration import RegistrationCreate, RegistrationResponse
from app.schemas.tournament import TournamentCreate, TournamentListResponse, TournamentResponse
from app.services.registration_service import RegistrationService
from app.services.tournament_service import TournamentService

router = APIRouter(tags=["tournaments"])


@router.get("/tournaments/available", response_model=list[TournamentListResponse])
def listar_torneos_disponibles(
    db: Session = Depends(get_db),
    _jugador_id: int = Depends(get_current_user),
) -> list[TournamentListResponse]:
    service = TournamentService(db)
    return service.obtener_torneos_disponibles()


@router.post("/tournaments", response_model=TournamentResponse, status_code=status.HTTP_201_CREATED)
def crear_torneo(
    payload: TournamentCreate,
    db: Session = Depends(get_db),
    creador_id: int = Depends(get_current_user),
) -> TournamentResponse:
    service = TournamentService(db)
    return service.crear_torneo(payload, creador_id)


@router.post("/tournaments/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def inscribirse_en_torneo(
    payload: RegistrationCreate,
    db: Session = Depends(get_db),
    jugador_id: int = Depends(get_current_user),
) -> RegistrationResponse:
    service = RegistrationService(db)
    return service.registrar_inscripcion(payload, jugador_id)
