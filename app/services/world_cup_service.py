from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.world_cup_repository import WorldCupRepository
from app.schemas.world_cup import WorldCupCreate


class WorldCupService:
    def __init__(self):
        self.repository = WorldCupRepository()

    def get_world_cups(self, db: Session):
        return self.repository.get_all(db)

    def get_world_cup_detail(self, db: Session, world_cup_id: int):
        world_cup = self.repository.get_by_id(db, world_cup_id)

        if not world_cup:
            raise HTTPException(status_code=404, detail="World Cup not found")

        return world_cup

    def get_world_cup_by_year(self, db: Session, year: int):
        world_cup = self.repository.get_by_year(db, year)

        if not world_cup:
            raise HTTPException(status_code=404, detail="World Cup not found")

        return world_cup

    def create_world_cup(self, db: Session, data: WorldCupCreate):
        existing_world_cup = self.repository.get_by_year(db, data.year)

        if existing_world_cup:
            raise HTTPException(status_code=400, detail="World Cup year already exists")

        return self.repository.create(db, data)
