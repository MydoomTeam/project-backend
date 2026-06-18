from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    message: str
    created_at: datetime
    status: str


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    stats: dict[str, int]
    history: list["AlertActivityResponse"]


class AlertActivityResponse(BaseModel):
    id: int
    action: str
    action_label: str | None = None
    created_at: datetime
    description: str | None = None
    tournament_id: int | None = None
    tournament_name: str | None = None


class AckResponse(BaseModel):
    message: str
