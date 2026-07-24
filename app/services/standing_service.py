from sqlalchemy.orm import Session

from app.repositories.standing_repository import StandingRepository


class StandingService:
    def __init__(self):
        self.repository = StandingRepository()

    def get_standings_by_world_cup(self, db: Session, world_cup_id: int):
        return self.repository.get_by_world_cup(db, world_cup_id)

    def get_standings_by_world_cup_group(self, db: Session, world_cup_id: int, group_name: str):
        return self.repository.get_by_world_cup_group(db, world_cup_id, group_name)
