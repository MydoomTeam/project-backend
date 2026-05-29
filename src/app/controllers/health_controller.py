from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.models.jugador import Jugador

router = APIRouter(tags=["health"])


@router.get("/hola")
def hola_mundo(db: Session = Depends(get_db)):
    db.query(Jugador).first()
    return {"message": "Hola Mundo con BD"}
