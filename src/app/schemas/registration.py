from pydantic import BaseModel, ConfigDict, Field


class RegistrationCreate(BaseModel):
    tournament_id: int = Field(gt=0)


class RegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tournament_id: int
    player_id: int
    status: str
