from sqlalchemy.orm import Session

from app.models.news import News
from app.schemas.news import NewsCreate


class NewsRepository:
    def get_all(self, db: Session):
        return db.query(News).order_by(News.published_at.desc()).all()

    def get_by_id(self, db: Session, news_id: int):
        return db.query(News).filter(News.id == news_id).first()

    def get_by_world_cup(self, db: Session, world_cup_id: int):
        return db.query(News).filter(News.world_cup_id == world_cup_id).all()

    def create(self, db: Session, data: NewsCreate):
        news = News(**data.model_dump())
        db.add(news)
        db.commit()
        db.refresh(news)
        return news
