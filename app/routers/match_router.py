from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.match import MatchCreate, MatchResponse
from app.services.match_service import MatchService


router = APIRouter(prefix="/matches", tags=["Matches"])
service = MatchService()


@router.get("/", response_model=list[MatchResponse])
def get_matches(db: Session = Depends(get_db)):
    return service.get_matches(db)


@router.get("/{match_id}", response_model=MatchResponse)
def get_match_detail(match_id: int, db: Session = Depends(get_db)):
    return service.get_match_detail(db, match_id)


@router.get("/world-cup/{world_cup_id}", response_model=list[MatchResponse])
def get_matches_by_world_cup(world_cup_id: int, db: Session = Depends(get_db)):
    return service.get_matches_by_world_cup(db, world_cup_id)


@router.post("/", response_model=MatchResponse)
def create_match(data: MatchCreate, db: Session = Depends(get_db)):
    return service.create_match(db, data)
