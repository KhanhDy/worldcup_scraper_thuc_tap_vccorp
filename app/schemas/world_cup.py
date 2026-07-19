from pydantic import BaseModel, ConfigDict


class WorldCupBase(BaseModel):
    year: int
    host_country: str
    champion_team_id: int | None = None
    runner_up_team_id: int | None = None


class WorldCupCreate(WorldCupBase):
    pass


class WorldCupResponse(WorldCupBase):
    id: int

    model_config = ConfigDict(from_attributes=True)