from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.schemas.match import MatchResponse, ResultadoRequest, ResultadoResponse
from app.schemas.registration import RegistrationCreate, RegistrationResponse
from app.schemas.tournament import (
    BracketResponse,
    RankingResponse,
    TournamentCreate,
    TournamentDetailResponse,
    TournamentListResponse,
    TournamentResponse,
)
from app.services.match_service import MatchService
from app.services.registration_service import RegistrationService
from app.services.tournament_service import TournamentService

router = APIRouter(tags=["tournaments"])


@router.get("/tournaments/available", response_model=list[TournamentListResponse])
def listar_torneos_disponibles(
    db: Session = Depends(get_db),
    _jugador_id: int = Depends(get_current_user),
) -> list[TournamentListResponse]:
    return TournamentService(db).obtener_torneos_disponibles()


@router.post("/tournaments", response_model=TournamentResponse, status_code=status.HTTP_201_CREATED)
def crear_torneo(
    payload: TournamentCreate,
    db: Session = Depends(get_db),
    creador_id: int = Depends(get_current_user),
) -> TournamentResponse:
    return TournamentService(db).crear_torneo(payload, creador_id)


@router.post("/tournaments/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def inscribirse_en_torneo(
    payload: RegistrationCreate,
    db: Session = Depends(get_db),
    jugador_id: int = Depends(get_current_user),
) -> RegistrationResponse:
    return RegistrationService(db).registrar_inscripcion(payload, jugador_id)


@router.get("/tournaments/{torneo_id}", response_model=TournamentDetailResponse)
def obtener_detalle_torneo(
    torneo_id: int,
    db: Session = Depends(get_db),
    _jugador_id: int = Depends(get_current_user),
) -> TournamentDetailResponse:
    return TournamentService(db).obtener_detalle_torneo(torneo_id)


@router.get("/tournaments/{torneo_id}/bracket", response_model=BracketResponse)
def obtener_bracket(
    torneo_id: int,
    db: Session = Depends(get_db),
    _jugador_id: int = Depends(get_current_user),
) -> BracketResponse:
    return MatchService(db).obtener_bracket(torneo_id)


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
    return MatchService(db).generar_bracket(torneo_id, admin_id)


@router.post("/tournaments/{torneo_id}/iniciar", response_model=BracketResponse)
def iniciar_torneo(
    torneo_id: int,
    db: Session = Depends(get_db),
    admin_id: int = Depends(get_current_user),
) -> BracketResponse:
    return MatchService(db).iniciar_torneo(torneo_id, admin_id)


@router.post(
    "/tournaments/{torneo_id}/matches/{match_id}/resultado",
    response_model=ResultadoResponse,
)
def registrar_resultado(
    torneo_id: int,
    match_id: int,
    payload: ResultadoRequest,
    db: Session = Depends(get_db),
    admin_id: int = Depends(get_current_user),
) -> ResultadoResponse:
    return MatchService(db).registrar_resultado(torneo_id, match_id, payload.ganador_id, admin_id)


@router.get("/tournaments/{torneo_id}/ranking", response_model=RankingResponse)
def obtener_ranking(
    torneo_id: int,
    db: Session = Depends(get_db),
    _jugador_id: int = Depends(get_current_user),
) -> RankingResponse:
    return MatchService(db).obtener_ranking(torneo_id)


@router.get("/tournaments/{torneo_id}/jugadores/{jugador_id}/historial", response_model=list[MatchResponse])
def obtener_historial_jugador(
    torneo_id: int,
    jugador_id: int,
    db: Session = Depends(get_db),
    _jugador_id: int = Depends(get_current_user),
) -> list[MatchResponse]:
    return MatchService(db).obtener_historial_jugador(torneo_id, jugador_id)


@router.post("/tournaments/{torneo_id}/cancelar", status_code=status.HTTP_204_NO_CONTENT)
def cancelar_torneo(
    torneo_id: int,
    db: Session = Depends(get_db),
    admin_id: int = Depends(get_current_user),
) -> None:
    TournamentService(db).cancelar_torneo(torneo_id, admin_id)


@router.delete("/tournaments/{torneo_id}/inscripcion", status_code=status.HTTP_204_NO_CONTENT)
def cancelar_inscripcion(
    torneo_id: int,
    db: Session = Depends(get_db),
    jugador_id: int = Depends(get_current_user),
) -> None:
    RegistrationService(db).cancelar_inscripcion(torneo_id, jugador_id)
