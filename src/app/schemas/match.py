from datetime import date

from pydantic import BaseModel, ConfigDict


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tournament_id: int
    round: int
    position: int
    bracket_type: str
    player1_id: int | None
    player2_id: int | None
    winner_id: int | None
    next_match_id: int | None = None
    score_detail: str | None = None
    scheduled_datetime: date | None = None
    result: str | None = None
    status: str


class ResultRequest(BaseModel):
    winner_id: int


class ResultResponse(BaseModel):
    match: MatchResponse
    winner_new_elo: int
    loser_new_elo: int
    tournament_finished: bool
