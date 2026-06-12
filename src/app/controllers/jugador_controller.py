from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import create_access_token
from app.core.database import get_db
from app.domain.schemas.jugador import JugadorRead, LoginRequest, LoginResponse, UsuarioRegistro
from app.services.jugador_service import JugadorService

router = APIRouter(tags=["jugadores"])


@router.get("/jugadores/{jugador_id}", response_model=JugadorRead)
def get_player(jugador_id: int, db: Session = Depends(get_db)):
    jugador = JugadorService(db).get_player(jugador_id)
    if jugador is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jugador no encontrado")
    return jugador


@router.post("/usuarios/registrar", response_model=JugadorRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UsuarioRegistro, db: Session = Depends(get_db)):
    outcome = JugadorService(db).register_user(payload)
    if outcome.is_duplicate:
        errores = []
        if outcome.duplicate_username:
            errores.append("nombre de usuario ya registrado")
        if outcome.duplicate_email:
            errores.append("correo electrónico ya registrado")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=errores)
    return outcome.jugador


@router.post("/usuarios/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    jugador = JugadorService(db).login(payload)
    if jugador is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    return LoginResponse(
        access_token=create_access_token(jugador.id),
        jugador=JugadorRead.model_validate(jugador),
    )
