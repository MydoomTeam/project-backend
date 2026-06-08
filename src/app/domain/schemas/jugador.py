from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from pydantic import Field
from pydantic import field_validator

import re

VALID_PATTERN = r"^[A-Za-z0-9!@#$%^&*()_\-+=\[\]{};:'\",.<>/?\\|`~ ]+$"

class JugadorCreate(BaseModel):
    id: int
    nombre_usuario: str
    correo_electronico: str
    contrasena_hash: str
    rol: str
    fecha_ultimo_acceso: date
    elo_global: int


class JugadorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_usuario: str
    correo_electronico: str
    rol: str
    fecha_ultimo_acceso: date
    elo_global: int


class UsuarioRegistro(BaseModel):
    nombre_usuario:str = Field(min_length=3,max_length=30)
    correo_electronico:EmailStr
    contrasena:str = Field(min_length=8)
    @field_validator("nombre_usuario","contrasena")

    @classmethod
    def validar_caracteres(cls,value):
        if not re.match(VALID_PATTERN,value):
            raise ValueError("Caracteres inválidos")
        return value
    
class LoginRequest(BaseModel):
    identificador:str
    contrasena:str
    @field_validator("identificador","contrasena")

    @classmethod
    def validar(cls,value):
        if not re.match(VALID_PATTERN,value):
            raise ValueError("Caracteres inválidos")
        return value


class LoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    jugador: JugadorRead