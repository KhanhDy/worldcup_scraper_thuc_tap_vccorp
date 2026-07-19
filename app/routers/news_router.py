from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.news import NewsCreate, NewsResponse
from app.services.news_service import NewsService


router = APIRouter(prefix="/news", tags=["News"])
service = NewsService()


@router.get("/", response_model=list[NewsResponse])
def get_news(db: Session = Depends(get_db)):
    return service.get_news(db)


@router.get("/{news_id}", response_model=NewsResponse)
def get_news_detail(news_id: int, db: Session = Depends(get_db)):
    return service.get_news_detail(db, news_id)


@router.get("/world-cup/{world_cup_id}", response_model=list[NewsResponse])
def get_news_by_world_cup(world_cup_id: int, db: Session = Depends(get_db)):
    return service.get_news_by_world_cup(db, world_cup_id)


@router.post("/", response_model=NewsResponse)
def create_news(data: NewsCreate, db: Session = Depends(get_db)):
    return service.create_news(db, data)
