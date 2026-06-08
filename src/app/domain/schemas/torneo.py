from pydantic import BaseModel
from typing import Optional

class TorneoCreate(BaseModel):
    nombre: str
    tipo_eliminacion: str
    duracion_ronda_min: int
    participantes_max: int

class TorneoResponse(BaseModel):
    id: int
    nombre: str
    estado: str
    opciones_siguientes: list[str]

    class Config:
        from_attributes = True

class TorneoDetailResponse(BaseModel):
    id: int
    nombre: str
    estado: str
    metadata: Optional[dict] = None

    class Config:
        from_attributes = True
