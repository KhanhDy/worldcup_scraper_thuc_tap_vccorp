from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StandingBase(BaseModel):
    world_cup_id: int
    team_id: int
    group_name: str
    rank: int
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    qualified: bool


class StandingCreate(StandingBase):
    pass


class StandingResponse(StandingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)