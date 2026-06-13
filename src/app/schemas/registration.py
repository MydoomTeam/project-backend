from pydantic import BaseModel, ConfigDict


class RegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tournament_id: int
    player_id: int
    status: str
