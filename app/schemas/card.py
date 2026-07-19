from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CardBase(BaseModel):
    match_id: int
    world_cup_id: int
    player_id: int
    team_id: int
    minute: int
    extra_minute: int | None = None
    card_type: str
    reason: str


class CardCreate(CardBase):
    pass


class CardResponse(CardBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)