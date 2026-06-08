from pydantic import BaseModel, ConfigDict


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    torneo_id: int
    ronda: int
    posicion: int
    bracket_tipo: str
    jugador1_id: int | None
    jugador2_id: int | None
    ganador_id: int | None
    estado: str


class ResultadoRequest(BaseModel):
    ganador_id: int


class ResultadoResponse(BaseModel):
    match: MatchResponse
    ganador_nuevo_elo: int
    perdedor_nuevo_elo: int
    torneo_finalizado: bool
