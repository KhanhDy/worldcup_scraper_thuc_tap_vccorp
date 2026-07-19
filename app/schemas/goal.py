from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GoalBase(BaseModel):
    match_id: int
    world_cup_id: int
    player_id: int
    team_id: int
    minute: int
    extra_minute: int | None = None
    is_penalty: bool = False
    is_own_goal: bool = False


class GoalCreate(GoalBase):
    pass


class GoalResponse(GoalBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)