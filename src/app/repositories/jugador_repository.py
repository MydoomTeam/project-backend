from sqlalchemy import select, or_
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
    
    def existe_usuario_o_correo(self, nombre_usuario:str, correo:str) -> bool:
        stmt = select(Jugador).where(or_(Jugador.nombre_usuario== nombre_usuario,Jugador.correo_electronico== correo))
        resultado = self.db.execute(stmt).scalars().first()
        return resultado is not None


    def siguiente_id(self) -> int:
        stmt = select(Jugador).order_by(Jugador.id.desc())
        ultimo = self.db.execute(stmt).scalars().first()
        if ultimo is None:
            return 1
        return ultimo.id + 1
