from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.player_repository import PlayerRepository
from app.schemas.player import PlayerCreate


class PlayerService:
    def __init__(self):
        self.repository = PlayerRepository()

    def get_players(self, db: Session):
        return self.repository.get_all(db)

    def get_player_detail(self, db: Session, player_id: int):
        player = self.repository.get_by_id(db, player_id)

        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        return player

    def create_player(self, db: Session, data: PlayerCreate):
        return self.repository.create(db, data)
