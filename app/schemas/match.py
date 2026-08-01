from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MatchBase(BaseModel):
    world_cup_id: int
    team_1_id: int
    team_2_id: int
    stage: str
    group_name: str | None = None
    match_date: datetime
    stadium: str
    city: str
    team_1_score: int
    team_2_score: int
    team_1_penalty_score: int | None = None
    team_2_penalty_score: int | None = None
    winner_team_id: int | None = None


class MatchCreate(MatchBase):
    pass


class MatchResponse(MatchBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)