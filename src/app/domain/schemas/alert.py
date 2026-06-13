from datetime import date

from pydantic import BaseModel, ConfigDict


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    message: str
    created_at: date
    status: str


class AlertListResponse(BaseModel):
    items: list[AlertResponse]


class AckResponse(BaseModel):
    message: str
