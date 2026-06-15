from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.schemas.match import MatchResponse, ResultRequest, ResultResponse
from app.schemas.registration import RegistrationResponse
from app.schemas.registration import RegistrationListItem, RegistrationStatusUpdate
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
def list_available_tournaments(
    db: Session = Depends(get_db),
    _player_id: int = Depends(get_current_user),
) -> list[TournamentListResponse]:
    tournaments = TournamentService(db).get_available_tournaments()
    return [TournamentListResponse.model_validate(item) for item in tournaments]


@router.get("/tournaments", response_model=list[TournamentListResponse])
def list_all_tournaments(
    db: Session = Depends(get_db),
    _player_id: int = Depends(get_current_user),
) -> list[TournamentListResponse]:
    tournaments = TournamentService(db).get_all_tournaments()
    return [TournamentListResponse.model_validate(item) for item in tournaments]


@router.post("/tournaments", response_model=TournamentResponse, status_code=status.HTTP_201_CREATED)
def create_tournament(
    payload: TournamentCreate,
    db: Session = Depends(get_db),
    creator_id: int = Depends(get_current_user),
) -> TournamentResponse:
    tournament = TournamentService(db).create_tournament(payload, creator_id)
    return TournamentResponse.model_validate(tournament)


@router.post(
    "/tournaments/{tournament_id}/registrations",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_in_tournament(
    tournament_id: int,
    db: Session = Depends(get_db),
    player_id: int = Depends(get_current_user),
) -> RegistrationResponse:
    registration = RegistrationService(db).register(tournament_id, player_id)
    return RegistrationResponse.model_validate(registration)


@router.get(
    "/tournaments/{tournament_id}/registrations",
    response_model=list[RegistrationListItem],
)
def list_tournament_registrations(
    tournament_id: int,
    db: Session = Depends(get_db),
    admin_id: int = Depends(get_current_user),
) -> list[RegistrationListItem]:
    return RegistrationService(db).list_tournament_registrations(tournament_id, admin_id)


@router.patch(
    "/tournaments/{tournament_id}/registrations/{player_id}",
    response_model=RegistrationResponse,
)
def update_registration_status(
    tournament_id: int,
    player_id: int,
    payload: RegistrationStatusUpdate,
    db: Session = Depends(get_db),
    admin_id: int = Depends(get_current_user),
) -> RegistrationResponse:
    registration = RegistrationService(db).update_registration_status(
        tournament_id=tournament_id,
        player_id=player_id,
        status_value=payload.status,
        admin_id=admin_id,
    )
    return RegistrationResponse.model_validate(registration)


@router.get("/tournaments/{tournament_id}", response_model=TournamentDetailResponse)
def get_tournament_detail(
    tournament_id: int,
    db: Session = Depends(get_db),
    _player_id: int = Depends(get_current_user),
) -> TournamentDetailResponse:
    return TournamentService(db).get_tournament_detail(tournament_id)


@router.get("/tournaments/{tournament_id}/bracket", response_model=BracketResponse)
def get_bracket(
    tournament_id: int,
    db: Session = Depends(get_db),
    _player_id: int = Depends(get_current_user),
) -> BracketResponse:
    return MatchService(db).get_bracket(tournament_id)


@router.post(
    "/tournaments/{tournament_id}/bracket",
    response_model=BracketResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_bracket(
    tournament_id: int,
    db: Session = Depends(get_db),
    admin_id: int = Depends(get_current_user),
) -> BracketResponse:
    return MatchService(db).generate_bracket(tournament_id, admin_id)


@router.post(
    "/tournaments/{tournament_id}/start",
    response_model=BracketResponse,
    status_code=status.HTTP_200_OK,
)
def start_tournament(
    tournament_id: int,
    db: Session = Depends(get_db),
    admin_id: int = Depends(get_current_user),
) -> BracketResponse:
    return MatchService(db).start_tournament(tournament_id, admin_id)


@router.post(
    "/tournaments/{tournament_id}/matches/{match_id}/result",
    response_model=ResultResponse,
    status_code=status.HTTP_200_OK,
)
def record_result(
    tournament_id: int,
    match_id: int,
    payload: ResultRequest,
    db: Session = Depends(get_db),
    admin_id: int = Depends(get_current_user),
) -> ResultResponse:
    return MatchService(db).record_result(tournament_id, match_id, payload.winner_id, admin_id)


@router.get("/tournaments/{tournament_id}/ranking", response_model=RankingResponse)
def get_ranking(
    tournament_id: int,
    db: Session = Depends(get_db),
    _player_id: int = Depends(get_current_user),
) -> RankingResponse:
    return MatchService(db).get_ranking(tournament_id)


@router.get("/tournaments/{tournament_id}/players/{player_id}/history", response_model=list[MatchResponse])
def get_player_history(
    tournament_id: int,
    player_id: int,
    db: Session = Depends(get_db),
    _player_id: int = Depends(get_current_user),
) -> list[MatchResponse]:
    return MatchService(db).get_player_history(tournament_id, player_id)


@router.delete("/tournaments/{tournament_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_tournament(
    tournament_id: int,
    db: Session = Depends(get_db),
    admin_id: int = Depends(get_current_user),
) -> None:
    TournamentService(db).cancel_tournament(tournament_id, admin_id)


@router.delete("/tournaments/{tournament_id}/registrations", status_code=status.HTTP_204_NO_CONTENT)
def cancel_registration(
    tournament_id: int,
    db: Session = Depends(get_db),
    player_id: int = Depends(get_current_user),
) -> None:
    RegistrationService(db).cancel_registration(tournament_id, player_id)
