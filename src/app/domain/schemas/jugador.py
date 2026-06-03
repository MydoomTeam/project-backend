from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, EmailStr


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
    nombre_usuario: str = Field(min_length=3,max_length=30)
    correo_electronico: EmailStr
    contrasena: str = Field(min_length=8)
