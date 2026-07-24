from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.standing import StandingTableResponse
from app.services.standing_service import StandingService


router = APIRouter(prefix="/standings", tags=["Standings"])
service = StandingService()


@router.get("/world-cup/{world_cup_id}", response_model=list[StandingTableResponse])
def get_standings_by_world_cup(world_cup_id: int, db: Session = Depends(get_db)):
    return service.get_standings_by_world_cup(db, world_cup_id)


@router.get("/world-cup/{world_cup_id}/groups/{group_name}", response_model=list[StandingTableResponse])
def get_standings_by_world_cup_group(
    world_cup_id: int,
    group_name: str,
    db: Session = Depends(get_db),
):
    return service.get_standings_by_world_cup_group(db, world_cup_id, group_name)
