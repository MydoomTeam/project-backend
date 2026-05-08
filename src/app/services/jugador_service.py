from sqlalchemy.orm import Session

from app.domain.models.jugador import Jugador
from app.domain.schemas.jugador import JugadorCreate
from app.repositories.jugador_repository import JugadorRepository


class JugadorService:
    def __init__(self, db: Session):
        self.repo = JugadorRepository(db)

    def crear_jugador(self, data: JugadorCreate) -> Jugador:
        jugador = Jugador(
            id=data.id,
            nombre_usuario=data.nombre_usuario,
            correo_electronico=data.correo_electronico,
            contrasena_hash=data.contrasena_hash,
            rol=data.rol,
            fecha_ultimo_acceso=data.fecha_ultimo_acceso,
            elo_global=data.elo_global,
        )
        return self.repo.crear(jugador)

    def obtener_jugador(self, jugador_id: int) -> Jugador | None:
        return self.repo.obtener_por_id(jugador_id)
