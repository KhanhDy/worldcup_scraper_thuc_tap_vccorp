from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.world_cup import WorldCupCreate, WorldCupResponse
from app.services.world_cup_service import WorldCupService


router = APIRouter(prefix="/world-cups", tags=["World Cups"])
service = WorldCupService()


@router.get("/", response_model=list[WorldCupResponse])
def get_world_cups(db: Session = Depends(get_db)):
    return service.get_world_cups(db)


@router.get("/{world_cup_id}", response_model=WorldCupResponse)
def get_world_cup_detail(world_cup_id: int, db: Session = Depends(get_db)):
    return service.get_world_cup_detail(db, world_cup_id)


@router.get("/year/{year}", response_model=WorldCupResponse)
def get_world_cup_by_year(year: int, db: Session = Depends(get_db)):
    return service.get_world_cup_by_year(db, year)


@router.post("/", response_model=WorldCupResponse)
def create_world_cup(data: WorldCupCreate, db: Session = Depends(get_db)):
    return service.create_world_cup(db, data)
