from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.schemas.registration import RegistrationCreate, RegistrationResponse
from app.schemas.tournament import BracketResponse, TournamentCreate, TournamentDetailResponse, TournamentListResponse, TournamentResponse
from app.services.match_service import MatchService
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


@router.get("/tournaments/{torneo_id}", response_model=TournamentDetailResponse)
def obtener_detalle_torneo(
    torneo_id: int,
    db: Session = Depends(get_db),
    _jugador_id: int = Depends(get_current_user),
) -> TournamentDetailResponse:
    service = TournamentService(db)
    return service.obtener_detalle_torneo(torneo_id)


@router.get("/tournaments/{torneo_id}/bracket", response_model=BracketResponse)
def obtener_bracket(
    torneo_id: int,
    db: Session = Depends(get_db),
    _jugador_id: int = Depends(get_current_user),
) -> BracketResponse:
    service = MatchService(db)
    return service.obtener_bracket(torneo_id)


@router.post(
    "/tournaments/{torneo_id}/bracket",
    response_model=BracketResponse,
    status_code=status.HTTP_201_CREATED,
)
def generar_bracket(
    torneo_id: int,
    db: Session = Depends(get_db),
    admin_id: int = Depends(get_current_user),
) -> BracketResponse:
    service = MatchService(db)
    return service.generar_bracket(torneo_id, admin_id)
