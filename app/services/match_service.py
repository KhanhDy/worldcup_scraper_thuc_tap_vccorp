from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.match_repository import MatchRepository
from app.schemas.match import MatchCreate


class MatchService:
    def __init__(self):
        self.repository = MatchRepository()

    def get_matches(self, db: Session):
        return self.repository.get_all(db)

    def get_match_detail(self, db: Session, match_id: int):
        match = self.repository.get_by_id(db, match_id)

        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        return match

    def get_matches_by_world_cup(self, db: Session, world_cup_id: int):
        return self.repository.get_by_world_cup(db, world_cup_id)

    def create_match(self, db: Session, data: MatchCreate):
        return self.repository.create(db, data)
