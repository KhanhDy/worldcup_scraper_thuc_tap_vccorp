from datetime import date

from pydantic import BaseModel, ConfigDict


class PlayerBase(BaseModel):
	full_name: str
	date_of_birth: date | None = None
	position: str | None = None
	team_id: int | None = None


class PlayerCreate(PlayerBase):
	pass


class PlayerResponse(PlayerBase):
	id: int

	model_config = ConfigDict(from_attributes=True)
