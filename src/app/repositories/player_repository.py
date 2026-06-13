from datetime import date

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.domain.models.player import Player


class PlayerRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, player: Player) -> Player:
        self.db.add(player)
        self.db.commit()
        self.db.refresh(player)
        return player

    def get_by_id(self, jugador_id: int) -> Player | None:
        stmt = select(Player).where(Player.id == jugador_id)
        return self.db.execute(stmt).scalars().first()

    def ensure_system_user(self, jugador_id: int) -> Player:
        """Garantiza un Player de sistema con id fijo, actor de los eventos
        automáticos (scheduler). Satisface la FK audit_logs.usuario_id -> jugador.id.
        """
        existing = self.get_by_id(jugador_id)
        if existing is not None:
            return existing

        player = Player(
            id=jugador_id,
            nombre_usuario="system",
            correo_electronico="system@localhost",
            contrasena_hash="",
            rol="JUGADOR",
            fecha_ultimo_acceso=date.today(),
            elo_global=0,
        )
        self.db.add(player)
        self.db.commit()
        self.db.refresh(player)
        return player

    def next_id(self) -> int:
        stmt = select(Player).order_by(Player.id.desc())
        last = self.db.execute(stmt).scalars().first()
        if last is None:
            return 1
        return last.id + 1

    def get_duplicates(self, nombre_usuario: str, email: str):
        existing_username = self.db.execute(
            select(Player).where(Player.nombre_usuario == nombre_usuario)
        ).scalars().first()
        existing_email = self.db.execute(
            select(Player).where(Player.correo_electronico == email)
        ).scalars().first()
        return {
            "username": existing_username is not None,
            "email": existing_email is not None,
        }

    def get_by_login(self, identifier: str) -> Player | None:
        stmt = select(Player).where(
            or_(Player.nombre_usuario == identifier, Player.correo_electronico == identifier)
        )
        return self.db.execute(stmt).scalars().first()

    def update_last_access(self, player: Player) -> Player:
        player.fecha_ultimo_acceso = date.today()
        self.db.commit()
        self.db.refresh(player)
        return player

    def update_password(self, player: Player, password_hash: str) -> Player:
        player.contrasena_hash = password_hash
        self.db.commit()
        self.db.refresh(player)
        return player
