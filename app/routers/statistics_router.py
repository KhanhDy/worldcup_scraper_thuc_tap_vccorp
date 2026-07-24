from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.statistics import TopMatchResponse, TopPlayerResponse, TopTeamResponse
from app.services.statistics_service import StatisticsService


router = APIRouter(prefix="/statistics", tags=["Statistics"])
service = StatisticsService()


@router.get("/teams/most-titles", response_model=list[TopTeamResponse])
def get_teams_most_titles(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.get_teams_most_titles(db, limit=limit)


@router.get("/players/top-scorers", response_model=list[TopPlayerResponse])
def get_players_top_scorers(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.get_players_top_scorers(db, limit=limit)


@router.get("/matches/most-goals", response_model=list[TopMatchResponse])
def get_matches_most_goals(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.get_matches_most_goals(db, limit=limit)


@router.get("/matches/most-cards", response_model=list[TopMatchResponse])
def get_matches_most_cards(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.get_matches_most_cards(db, limit=limit)


@router.get("/players/most-appearances", response_model=list[TopPlayerResponse])
def get_players_most_appearances(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.get_players_most_appearances(db, limit=limit)
