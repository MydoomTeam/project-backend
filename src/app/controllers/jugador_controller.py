from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.schemas.jugador import JugadorCreate, JugadorRead
from app.services.jugador_service import JugadorService
from app.domain.schemas.jugador import UsuarioRegistro
from app.domain.schemas.jugador import LoginRequest

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
    resultado = service.registrar_usuario(payload)
    if isinstance(resultado,dict):
        duplicados = resultado["duplicados"]
        errores = []
        if duplicados["usuario"]:
            errores.append("nombre de usuario ya registrado")
        if duplicados["correo"]:
            errores.append("correo electrónico ya registrado")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail=errores)
    return resultado

@router.post("/usuarios/login", response_model=JugadorRead)
def iniciar_sesion(payload: LoginRequest, db: Session = Depends(get_db)):
    service = JugadorService(db)
    jugador = service.iniciar_sesion(payload)
    if jugador is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    return jugador
