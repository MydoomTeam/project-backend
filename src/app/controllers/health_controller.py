from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/hola")
def hola_mundo(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"message": "Hola Mundo con BD"}
