from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.news_repository import NewsRepository
from app.schemas.news import NewsCreate


class NewsService:
    def __init__(self):
        self.repository = NewsRepository()

    def get_news(self, db: Session):
        return self.repository.get_all(db)

    def get_news_detail(self, db: Session, news_id: int):
        news = self.repository.get_by_id(db, news_id)

        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        return news

    def get_news_by_world_cup(self, db: Session, world_cup_id: int):
        return self.repository.get_by_world_cup(db, world_cup_id)

    def create_news(self, db: Session, data: NewsCreate):
        return self.repository.create(db, data)
