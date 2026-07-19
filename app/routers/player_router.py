from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.player import PlayerCreate, PlayerResponse
from app.services.player_service import PlayerService


router = APIRouter(prefix="/players", tags=["Players"])
service = PlayerService()


@router.get("/", response_model=list[PlayerResponse])
def get_players(db: Session = Depends(get_db)):
    return service.get_players(db)


@router.get("/{player_id}", response_model=PlayerResponse)
def get_player_detail(player_id: int, db: Session = Depends(get_db)):
    return service.get_player_detail(db, player_id)


@router.post("/", response_model=PlayerResponse)
def create_player(data: PlayerCreate, db: Session = Depends(get_db)):
    return service.create_player(db, data)
