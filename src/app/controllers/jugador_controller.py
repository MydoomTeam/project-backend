from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.schemas.jugador import JugadorCreate, JugadorRead
from app.services.jugador_service import JugadorService
from app.domain.schemas.jugador import UsuarioRegistro

router = APIRouter(tags=["jugadores"])


@router.post("/jugadores", response_model=JugadorRead, status_code=status.HTTP_201_CREATED)
def crear_jugador(payload: JugadorCreate, db: Session = Depends(get_db)):
    service = JugadorService(db)
    return service.crear_jugador(payload)


@router.get("/jugadores/{jugador_id}", response_model=JugadorRead)
def obtener_jugador(jugador_id: int, db: Session = Depends(get_db)):
    service = JugadorService(db)
    jugador = service.obtener_jugador(jugador_id)
    if jugador is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jugador no encontrado")
    return jugador

@router.post("/usuarios/registrar", response_model=JugadorRead, status_code=status.HTTP_201_CREATED)
def registrar_usuario(payload: UsuarioRegistro,db: Session = Depends(get_db)):
    service = JugadorService(db)
    jugador = service.registrar_usuario(payload)
    if jugador is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuario o correo ya existe")
    return jugador
