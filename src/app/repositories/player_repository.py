from datetime import date

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.domain.models.player import Player


class PlayerRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, jugador: Player) -> Player:
        self.db.add(jugador)
        self.db.commit()
        self.db.refresh(jugador)
        return jugador

    def get_by_id(self, jugador_id: int) -> Player | None:
        stmt = select(Player).where(Player.id == jugador_id)
        return self.db.execute(stmt).scalars().first()

    def ensure_system_user(self, jugador_id: int) -> Player:
        """Garantiza un Player de sistema con id fijo, actor de los eventos
        automáticos (scheduler). Satisface la FK audit_logs.usuario_id -> jugador.id.
        """
        existente = self.get_by_id(jugador_id)
        if existente is not None:
            return existente

        jugador = Player(
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

    def next_id(self) -> int:
        stmt = select(Player).order_by(Player.id.desc())
        ultimo = self.db.execute(stmt).scalars().first()
        if ultimo is None:
            return 1
        return ultimo.id + 1

    def get_duplicates(self, nombre_usuario: str, correo: str):
        usuario_existente = self.db.execute(
            select(Player).where(Player.nombre_usuario == nombre_usuario)
        ).scalars().first()
        correo_existente = self.db.execute(
            select(Player).where(Player.correo_electronico == correo)
        ).scalars().first()
        return {
            "usuario": usuario_existente is not None,
            "correo": correo_existente is not None,
        }

    def get_by_login(self, identificador: str) -> Player | None:
        stmt = select(Player).where(
            or_(Player.nombre_usuario == identificador, Player.correo_electronico == identificador)
        )
        return self.db.execute(stmt).scalars().first()

    def update_last_access(self, jugador: Player) -> Player:
        jugador.fecha_ultimo_acceso = date.today()
        self.db.commit()
        self.db.refresh(jugador)
        return jugador

    def update_password(self, jugador: Player, password_hash: str) -> Player:
        jugador.contrasena_hash = password_hash
        self.db.commit()
        self.db.refresh(jugador)
        return jugador
