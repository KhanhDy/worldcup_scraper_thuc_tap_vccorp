from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.team import TeamCreate, TeamResponse
from app.services.team_service import TeamService


router = APIRouter(prefix="/teams", tags=["Teams"])
service = TeamService()


@router.get("/", response_model=list[TeamResponse])
def get_teams(db: Session = Depends(get_db)):
    return service.get_teams(db)


@router.get("/{team_id}", response_model=TeamResponse)
def get_team_detail(team_id: int, db: Session = Depends(get_db)):
    return service.get_team_detail(db, team_id)


@router.post("/", response_model=TeamResponse)
def create_team(data: TeamCreate, db: Session = Depends(get_db)):
    return service.create_team(db, data)