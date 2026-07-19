from sqlalchemy.orm import Session

from app.models.matches import Match
from app.schemas.match import MatchCreate


class MatchRepository:
    def get_all(self, db: Session):
        return db.query(Match).order_by(Match.match_date.desc()).all()

    def get_by_id(self, db: Session, match_id: int):
        return db.query(Match).filter(Match.id == match_id).first()

    def get_by_world_cup(self, db: Session, world_cup_id: int):
        return db.query(Match).filter(Match.world_cup_id == world_cup_id).all()

    def create(self, db: Session, data: MatchCreate):
        match = Match(**data.model_dump())
        db.add(match)
        db.commit()
        db.refresh(match)
        return match
