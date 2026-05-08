from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.schemas.jugador import JugadorCreate, JugadorRead
from app.services.jugador_service import JugadorService

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
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    return jugador
