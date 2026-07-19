from pydantic import BaseModel


class TopTeamResponse(BaseModel):
    team_id: int
    team_name: str
    titles: int


class TopPlayerResponse(BaseModel):
    player_id: int
    player_name: str
    total: int


class TopMatchResponse(BaseModel):
    match_id: int
    world_cup_id: int
    description: str
    total: int