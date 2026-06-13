from pydantic import BaseModel, ConfigDict, Field

from app.schemas.match import MatchResponse


class TournamentCreate(BaseModel):
    name: str = Field(min_length=1)
    elimination_type: str = Field(min_length=1)
    rounds: int = Field(gt=0)


class TournamentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    elimination_type: str
    rounds: int
    status: str
    creator_id: int


class TournamentListResponse(TournamentResponse):
    pass


class BracketResponse(BaseModel):
    tournament_id: int
    tournament_status: str
    matches: list[MatchResponse]


class TournamentDetailResponse(BaseModel):
    id: int
    name: str
    elimination_type: str
    rounds: int
    status: str
    creator_id: int
    creator_name: str
    total_participants: int


class RankingEntry(BaseModel):
    position: int
    player_id: int
    wins: int
    global_elo: int


class RankingResponse(BaseModel):
    tournament_id: int
    elimination_type: str
    status: str
    ranking: list[RankingEntry]
