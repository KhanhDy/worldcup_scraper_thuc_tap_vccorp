from sqlalchemy.orm import Session

from app.models.team import Team
from app.schemas.team import TeamCreate


class TeamRepository:
    def get_all(self, db: Session):
        return db.query(Team).order_by(Team.name).all()

    def get_by_id(self, db: Session, team_id: int):
        return db.query(Team).filter(Team.id == team_id).first()

    def create(self, db: Session, data: TeamCreate):
        team = Team(**data.model_dump())
        db.add(team)
        db.commit()
        db.refresh(team)
        return team