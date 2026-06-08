from pydantic import BaseModel, ConfigDict


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    torneo_id: int
    ronda: int
    jugador1_id: int
    jugador2_id: int | None
    estado: str
