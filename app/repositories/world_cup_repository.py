from sqlalchemy.orm import Session

from app.models.world_cup import WorldCup
from app.schemas.world_cup import WorldCupCreate


class WorldCupRepository:
    def get_all(self, db: Session):
        return db.query(WorldCup).order_by(WorldCup.year.desc()).all()

    def get_by_id(self, db: Session, world_cup_id: int):
        return db.query(WorldCup).filter(WorldCup.id == world_cup_id).first()

    def get_by_year(self, db: Session, year: int):
        return db.query(WorldCup).filter(WorldCup.year == year).first()

    def create(self, db: Session, data: WorldCupCreate):
        world_cup = WorldCup(**data.model_dump())
        db.add(world_cup)
        db.commit()
        db.refresh(world_cup)
        return world_cup
