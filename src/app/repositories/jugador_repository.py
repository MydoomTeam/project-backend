from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.jugador import Jugador


class JugadorRepository:
    def __init__(self, db: Session):
        self.db = db

    def crear(self, jugador: Jugador) -> Jugador:
        self.db.add(jugador)
        self.db.commit()
        self.db.refresh(jugador)
        return jugador

    def obtener_por_id(self, jugador_id: int) -> Jugador | None:
        stmt = select(Jugador).where(Jugador.id == jugador_id)
        return self.db.execute(stmt).scalars().first()
