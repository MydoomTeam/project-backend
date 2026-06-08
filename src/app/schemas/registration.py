from pydantic import BaseModel, ConfigDict, Field


class RegistrationCreate(BaseModel):
    torneo_id: int = Field(gt=0)


class RegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    torneo_id: int
    jugador_id: int
    estado: str
