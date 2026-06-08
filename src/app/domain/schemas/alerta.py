from datetime import date

from pydantic import BaseModel, ConfigDict


class AlertaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    mensaje: str
    created_at: date
    status: str


class AlertaListResponse(BaseModel):
    items: list[AlertaResponse]


class AckResponse(BaseModel):
    message: str
