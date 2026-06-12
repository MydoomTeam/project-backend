from dataclasses import dataclass
from datetime import date
import logging

import bcrypt
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domain.models.jugador import Jugador
from app.domain.schemas.jugador import LoginRequest, PasswordUpdate, UsuarioRegistro
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.jugador_repository import JugadorRepository

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

    jugador: Jugador | None = None
    duplicate_username: bool = False
    duplicate_email: bool = False

    @property
    def is_duplicate(self) -> bool:
        return self.duplicate_username or self.duplicate_email


class JugadorService:
    def __init__(self, db: Session):
        self.repo = JugadorRepository(db)
        self.audit_repo = AuditLogRepository(db)

    def get_player(self, jugador_id: int) -> Jugador | None:
        return self.repo.get_by_id(jugador_id)

    def _validate_password(self, password: str) -> None:
        for is_valid, message in _PASSWORD_RULES:
            if not is_valid(password):
                raise HTTPException(
                    status_code=400,
                    detail={"error": "validation_error", "details": [message]},
                )

    def change_password(self, jugador_id: int, schema: PasswordUpdate):
        if schema.password != schema.password_confirm:
            raise HTTPException(
                status_code=400,
                detail={"error": "validation_error", "details": ["Las contraseñas no coinciden"]},
            )

        self._validate_password(schema.password)

        jugador = self.repo.get_by_id(jugador_id)
        if jugador is None:
            raise HTTPException(status_code=404, detail="Jugador no encontrado")

        password_hash = self._hash_password(schema.password)
        try:
            self.repo.update_password(jugador, password_hash)
            self.audit_repo.log_action(
                actor_id=jugador_id,
                accion="UPDATE_PASSWORD",
                descripcion_cambio="Jugador",
            )
        except Exception:
            self.audit_repo.log_action(
                actor_id=jugador_id,
                accion="UPDATE_PASSWORD_FAILED",
                descripcion_cambio="Jugador",
            )
            raise HTTPException(
                status_code=500,
                detail="Error al persistir en la base de datos",
            )

        return {"message": "password_updated"}

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    def register_user(self, data: UsuarioRegistro) -> RegistrationOutcome:
        duplicados = self.repo.get_duplicates(data.nombre_usuario, data.correo_electronico)
        if duplicados["usuario"] or duplicados["correo"]:
            return RegistrationOutcome(
                duplicate_username=duplicados["usuario"],
                duplicate_email=duplicados["correo"],
            )
        jugador = Jugador(
            id=self.repo.next_id(),
            nombre_usuario=data.nombre_usuario,
            correo_electronico=data.correo_electronico,
            contrasena_hash=self._hash_password(data.contrasena),
            rol="JUGADOR",
            elo_global=0,
            fecha_ultimo_acceso=date.today(),
        )
        creado = self.repo.create(jugador)
        logger.info(f"Usuario creado {creado.nombre_usuario}")
        return RegistrationOutcome(jugador=creado)

    def _verificar_password(self, password: str, almacenado: str | None) -> bool:
        # Verificación defensiva: hash vacío/None/no-bcrypt -> False, nunca lanza.
        # (El jugador de sistema tiene contrasena_hash="" y no es autenticable.)
        if not almacenado:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), almacenado.encode("utf-8"))
        except (ValueError, TypeError):
            return False

    def login(self, data: LoginRequest):
        jugador = self.repo.get_by_login(data.identificador)
        if jugador is None:
            return None
        if not self._verificar_password(data.contrasena, jugador.contrasena_hash):
            return None
        return self.repo.update_last_access(jugador)
