from sqlalchemy.orm import Session

from fastapi import HTTPException, status

from datetime import date

import hashlib
import secrets
import logging

from app.domain.models.jugador import Jugador
from app.domain.schemas.jugador import (JugadorCreate, LoginRequest, LoginResponse, UsuarioRegistro)
from app.repositories.jugador_repository import JugadorRepository
from app.domain.schemas.jugador import UsuarioRegistro
from app.core.auth import create_access_token


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

    def registrar_usuario(self, data:UsuarioRegistro):
        duplicados = self.repo.obtener_duplicados(data.nombre_usuario,data.correo_electronico)
        if (duplicados["usuario"] or duplicados["correo"]):
            return {"duplicados":duplicados}
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
    
    def _verificar_password(self, password:str, almacenado:str):
        salt, hash_guardado = almacenado.split("$")
        nuevo_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            100000
        ).hex()
        return nuevo_hash == hash_guardado
    
    def iniciar_sesion(self,data:LoginRequest) -> LoginResponse | None:
        jugador = self.repo.obtener_por_login(data.identificador)
        if jugador is None:
            return None
        valido = self._verificar_password(
            data.contrasena,
            jugador.contrasena_hash
        )
        if not valido:
            return None
        actualizado = self.repo.actualizar_ultimo_acceso(jugador)
        return LoginResponse(
            access_token=create_access_token(actualizado.id),
            jugador=actualizado,
        )

