from pydantic import BaseModel, ConfigDict, Field


class TournamentCreate(BaseModel):
    nombre: str = Field(min_length=1)
    tipo_eliminacion: str = Field(min_length=1)
    rondas: int = Field(gt=0)


class TournamentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    tipo_eliminacion: str
    rondas: int
    estado: str
    creador_id: int


class TournamentListResponse(TournamentResponse):
    pass
