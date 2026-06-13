from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import create_access_token
from app.core.database import get_db
from app.domain.schemas.player import PlayerRead, LoginRequest, LoginResponse, UserRegistration
from app.services.player_service import PlayerService

router = APIRouter(tags=["jugadores"])


@router.get("/jugadores/{jugador_id}", response_model=PlayerRead)
def get_player(jugador_id: int, db: Session = Depends(get_db)):
    player = PlayerService(db).get_player(jugador_id)
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jugador no encontrado")
    return player


@router.post("/usuarios/registrar", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegistration, db: Session = Depends(get_db)):
    outcome = PlayerService(db).register_user(payload)
    if outcome.is_duplicate:
        errors = []
        if outcome.duplicate_username:
            errors.append("nombre de usuario ya registrado")
        if outcome.duplicate_email:
            errors.append("correo electrónico ya registrado")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=errors)
    return outcome.player


@router.post("/usuarios/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    player = PlayerService(db).login(payload)
    if player is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    return LoginResponse(
        access_token=create_access_token(player.id),
        player=PlayerRead.model_validate(player),
    )
