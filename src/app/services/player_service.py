from dataclasses import dataclass
from datetime import date
import logging

import bcrypt
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domain.models.player import Player
from app.domain.schemas.player import EloHistoryItem, LoginRequest, PasswordUpdate, UserRegistration
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.elo_history_repository import EloHistoryRepository
from app.repositories.player_repository import PlayerRepository
from app.repositories.tournament_repository import TournamentRepository

logger = logging.getLogger(__name__)

_PASSWORD_RULES = [
    (lambda password: len(password) >= 8, "La contraseña debe tener al menos 8 caracteres"),
    (lambda password: any(char.isupper() for char in password), "La contraseña debe contener al menos una mayúscula"),
    (lambda password: any(char.islower() for char in password), "La contraseña debe contener al menos una minúscula"),
    (lambda password: any(char.isdigit() for char in password), "La contraseña debe contener al menos un número"),
]


@dataclass
class RegistrationOutcome:
    """Resultado explícito del registro: jugador creado o conflicto de duplicados."""

    player: Player | None = None
    duplicate_username: bool = False
    duplicate_email: bool = False

    @property
    def is_duplicate(self) -> bool:
        return self.duplicate_username or self.duplicate_email


class PlayerService:
    def __init__(self, db: Session):
        self.repo = PlayerRepository(db)
        self.audit_repo = AuditLogRepository(db)
        self.tournament_repo = TournamentRepository(db)
        self.elo_history_repo = EloHistoryRepository(db)

    def get_player(self, player_id: int) -> Player | None:
        return self.repo.get_by_id(player_id)

    def get_elo_history(self, player_id: int) -> list[EloHistoryItem]:
        player = self.repo.get_by_id(player_id)
        if player is None:
            raise HTTPException(status_code=404, detail="Jugador no encontrado")
        entries = self.elo_history_repo.get_by_player(player_id)
        return [EloHistoryItem.model_validate(entry) for entry in entries]

    def get_player_tournament_history(self, player_id: int) -> list[dict]:
        player = self.repo.get_by_id(player_id)
        if player is None:
            raise HTTPException(status_code=404, detail="Jugador no encontrado")

        rows = self.tournament_repo.list_player_tournament_history(player_id)
        return [
            {
                "id": tournament.id,
                "name": tournament.name,
                "elimination_type": tournament.elimination_type,
                "rounds": tournament.rounds,
                "status": tournament.status,
                "is_creator": tournament.creator_id == player_id,
                "registration_status": registration_status,
            }
            for tournament, registration_status in rows
        ]

    def _validate_password(self, password: str) -> None:
        for is_valid, message in _PASSWORD_RULES:
            if not is_valid(password):
                raise HTTPException(
                    status_code=400,
                    detail={"error": "validation_error", "details": [message]},
                )

    def change_password(self, player_id: int, schema: PasswordUpdate):
        if schema.password != schema.password_confirm:
            raise HTTPException(
                status_code=400,
                detail={"error": "validation_error", "details": ["Las contraseñas no coinciden"]},
            )

        self._validate_password(schema.password)

        player = self.repo.get_by_id(player_id)
        if player is None:
            raise HTTPException(status_code=404, detail="Jugador no encontrado")

        password_hash = self._hash_password(schema.password)
        try:
            self.repo.update_password(player, password_hash)
            self.audit_repo.log_action(
                actor_id=player_id,
                action="UPDATE_PASSWORD",
                change_description="Player",
            )
        except Exception:
            self.audit_repo.log_action(
                actor_id=player_id,
                action="UPDATE_PASSWORD_FAILED",
                change_description="Player",
            )
            raise HTTPException(
                status_code=500,
                detail="Error al persistir en la base de datos",
            )

        return {"message": "password_updated"}

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    def register_user(self, data: UserRegistration) -> RegistrationOutcome:
        duplicates = self.repo.get_duplicates(data.username, data.email)
        if duplicates["username"] or duplicates["email"]:
            return RegistrationOutcome(
                duplicate_username=duplicates["username"],
                duplicate_email=duplicates["email"],
            )
        player = Player(
            id=self.repo.next_id(),
            username=data.username,
            email=data.email,
            password_hash=self._hash_password(data.password),
            role="JUGADOR",
            global_elo=0,
            last_access_date=date.today(),
        )
        created = self.repo.create(player)
        logger.info(f"Usuario creado {created.username}")
        return RegistrationOutcome(player=created)

    def _verify_password(self, password: str, stored: str | None) -> bool:
        # Verificación defensiva: hash vacío/None/no-bcrypt -> False, nunca lanza.
        # (El jugador de sistema tiene password_hash="" y no es autenticable.)
        if not stored:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
        except (ValueError, TypeError):
            return False

    def login(self, data: LoginRequest):
        player = self.repo.get_by_login(data.identifier)
        if player is None:
            return None
        if not self._verify_password(data.password, player.password_hash):
            return None
        return self.repo.update_last_access(player)
