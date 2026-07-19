from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.repositories.team_repository import TeamRepository
from app.schemas.team import TeamCreate


class TeamService:
    def __init__(self):
        self.repository = TeamRepository()

    def get_teams(self, db: Session):
        return self.repository.get_all(db)

    def get_team_detail(self, db: Session, team_id: int):
        team = self.repository.get_by_id(db, team_id)

        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        return team

    def create_team(self, db: Session, data: TeamCreate):
        return self.repository.create(db, data)