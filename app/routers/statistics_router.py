from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.statistics import TopMatchResponse, TopPlayerResponse, TopTeamResponse
from app.services.statistics_service import StatisticsService


router = APIRouter(prefix="/statistics", tags=["Statistics"])
service = StatisticsService()


@router.get("/teams/most-titles", response_model=list[TopTeamResponse])
def get_teams_most_titles(db: Session = Depends(get_db)):
    return service.get_teams_most_titles(db)


@router.get("/players/top-scorers", response_model=list[TopPlayerResponse])
def get_players_top_scorers(db: Session = Depends(get_db)):
    return service.get_players_top_scorers(db)


@router.get("/matches/most-goals", response_model=list[TopMatchResponse])
def get_matches_most_goals(db: Session = Depends(get_db)):
    return service.get_matches_most_goals(db)


@router.get("/matches/most-cards", response_model=list[TopMatchResponse])
def get_matches_most_cards(db: Session = Depends(get_db)):
    return service.get_matches_most_cards(db)


@router.get("/players/most-appearances", response_model=list[TopPlayerResponse])
def get_players_most_appearances(db: Session = Depends(get_db)):
    return service.get_players_most_appearances(db)
