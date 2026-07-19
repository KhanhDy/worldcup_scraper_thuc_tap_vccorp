from sqlalchemy.orm import Session

from app.models.player import Player
from app.schemas.player import PlayerCreate


class PlayerRepository:
    def get_all(self, db: Session):
        return db.query(Player).order_by(Player.full_name).all()

    def get_by_id(self, db: Session, player_id: int):
        return db.query(Player).filter(Player.id == player_id).first()

    def create(self, db: Session, data: PlayerCreate):
        player = Player(**data.model_dump())
        db.add(player)
        db.commit()
        db.refresh(player)
        return player
