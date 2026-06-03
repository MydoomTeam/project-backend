from sqlalchemy.orm import Session

from fastapi import HTTPException, status

from datetime import date

import hashlib
import secrets
import logging

from app.domain.models.jugador import Jugador
from app.domain.schemas.jugador import (JugadorCreate, UsuarioRegistro)
from app.repositories.jugador_repository import JugadorRepository
from app.domain.schemas.jugador import UsuarioRegistro


logger = logging.getLogger(
    __name__
)

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
    
    def _hash_password(self,password:str):
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return f"{salt}${hashed.hex()}"

    def registrar_usuario(self,data:UsuarioRegistro):
        existe = self.repo.existe_usuario_o_correo(data.nombre_usuario, data.correo_electronico)
        if existe:
            return None
        jugador = Jugador(
            id=self.repo.siguiente_id(),
            nombre_usuario=data.nombre_usuario,
            correo_electronico=data.correo_electronico,
            contrasena_hash=self._hash_password(data.contrasena),
            rol="JUGADOR",
            elo_global=0,
            fecha_ultimo_acceso=date.today()
        )
        creado = self.repo.crear(jugador)
        logger.info(f"Usuario creado {creado.nombre_usuario}")
        return creado

