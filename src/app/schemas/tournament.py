from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.match import MatchResponse


class TournamentCreate(BaseModel):
    name: str = Field(min_length=1)
    elimination_type: str = Field(min_length=1)
    rounds: int = Field(gt=0)
    game_name: str | None = None
    game_category: str | None = None
    participant_target: int | None = Field(default=None, gt=0)
    round_duration_minutes: int | None = Field(default=None, gt=0)
    uses_score: bool = False
    start_date: date | None = None
    end_date: date | None = None
    language: str | None = None
    region: str | None = None


class TournamentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    elimination_type: str
    game_name: str | None = None
    game_category: str | None = None
    participant_target: int | None = None
    rounds: int
    round_duration_minutes: int | None = None
    uses_score: bool = False
    status: str
    start_date: date | None = None
    end_date: date | None = None
    language: str | None = None
    region: str | None = None
    creator_id: int
    creator_name: str | None = None
    creator_avatar_url: str | None = None


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
    game_name: str | None = None
    game_category: str | None = None
    participant_target: int | None = None
    rounds: int
    round_duration_minutes: int | None = None
    uses_score: bool = False
    status: str
    start_date: date | None = None
    end_date: date | None = None
    language: str | None = None
    region: str | None = None
    creator_id: int
    creator_name: str
    creator_avatar_url: str | None = None
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
