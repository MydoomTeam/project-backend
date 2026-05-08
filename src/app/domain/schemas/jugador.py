from datetime import date

from pydantic import BaseModel, ConfigDict


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
