from datetime import date

from pydantic import BaseModel, ConfigDict


class RegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tournament_id: int
    player_id: int
    status: str
    registration_date: date | None = None
    elo_seed: int | None = None


class RegistrationStatusUpdate(BaseModel):
    status: str


class RegistrationListItem(BaseModel):
    id: int
    tournament_id: int
    player_id: int
    username: str
    email: str
    status: str
    registration_date: date | None = None
    elo_seed: int | None = None
