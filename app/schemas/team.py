from pydantic import BaseModel, ConfigDict


class TeamBase(BaseModel):
    name: str
    fifa_code: str | None = None
    continent: str | None = None


class TeamCreate(TeamBase):
    pass


class TeamResponse(TeamBase):
    id: int

    model_config = ConfigDict(from_attributes=True)