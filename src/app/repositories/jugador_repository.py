from datetime import date

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

    def ensure_system_user(self, jugador_id: int) -> Jugador:
        """Garantiza un Jugador de sistema con id fijo, actor de los eventos
        automáticos (scheduler). Satisface la FK audit_logs.usuario_id -> jugador.id.
        """
        existente = self.obtener_por_id(jugador_id)
        if existente is not None:
            return existente

        jugador = Jugador(
            id=jugador_id,
            nombre_usuario="system",
            correo_electronico="system@localhost",
            contrasena_hash="",
            rol="JUGADOR",
            fecha_ultimo_acceso=date.today(),
            elo_global=0,
        )
        self.db.add(jugador)
        self.db.commit()
        self.db.refresh(jugador)
        return jugador

    def siguiente_id(self) -> int:
        stmt = select(Jugador).order_by(Jugador.id.desc())
        ultimo = self.db.execute(stmt).scalars().first()
        if ultimo is None:
            return 1
        return ultimo.id + 1

    def obtener_duplicados(self, nombre_usuario: str, correo: str):
        usuario_existente = self.db.execute(
            select(Jugador).where(Jugador.nombre_usuario == nombre_usuario)
        ).scalars().first()
        correo_existente = self.db.execute(
            select(Jugador).where(Jugador.correo_electronico == correo)
        ).scalars().first()
        return {
            "usuario": usuario_existente is not None,
            "correo": correo_existente is not None,
        }

    def obtener_por_login(self, identificador: str) -> Jugador | None:
        stmt = select(Jugador).where(
            or_(Jugador.nombre_usuario == identificador, Jugador.correo_electronico == identificador)
        )
        return self.db.execute(stmt).scalars().first()

    def actualizar_ultimo_acceso(self, jugador: Jugador) -> Jugador:
        jugador.fecha_ultimo_acceso = date.today()
        self.db.commit()
        self.db.refresh(jugador)
        return jugador
