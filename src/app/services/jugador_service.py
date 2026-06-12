from dataclasses import dataclass
from datetime import date
import hashlib
import logging
import secrets

from sqlalchemy.orm import Session

from app.domain.models.jugador import Jugador
from app.domain.schemas.jugador import LoginRequest, UsuarioRegistro
from app.repositories.jugador_repository import JugadorRepository

logger = logging.getLogger(__name__)


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

    def obtener_jugador(self, jugador_id: int) -> Jugador | None:
        return self.repo.obtener_por_id(jugador_id)

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return f"{salt}${hashed.hex()}"

    def registrar_usuario(self, data: UsuarioRegistro) -> RegistrationOutcome:
        duplicados = self.repo.obtener_duplicados(data.nombre_usuario, data.correo_electronico)
        if duplicados["usuario"] or duplicados["correo"]:
            return RegistrationOutcome(
                duplicate_username=duplicados["usuario"],
                duplicate_email=duplicados["correo"],
            )
        jugador = Jugador(
            id=self.repo.siguiente_id(),
            nombre_usuario=data.nombre_usuario,
            correo_electronico=data.correo_electronico,
            contrasena_hash=self._hash_password(data.contrasena),
            rol="JUGADOR",
            elo_global=0,
            fecha_ultimo_acceso=date.today(),
        )
        creado = self.repo.crear(jugador)
        logger.info(f"Usuario creado {creado.nombre_usuario}")
        return RegistrationOutcome(jugador=creado)

    def _verificar_password(self, password: str, almacenado: str) -> bool:
        salt, hash_guardado = almacenado.split("$")
        nuevo_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 100000
        ).hex()
        return nuevo_hash == hash_guardado

    def iniciar_sesion(self, data: LoginRequest):
        jugador = self.repo.obtener_por_login(data.identificador)
        if jugador is None:
            return None
        if not self._verificar_password(data.contrasena, jugador.contrasena_hash):
            return None
        return self.repo.actualizar_ultimo_acceso(jugador)
