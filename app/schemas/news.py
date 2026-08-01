from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NewsBase(BaseModel):
    title: str
    slug: str
    summary: str
    content: str
    url: str
    source: str
    author: str
    published_at: datetime
    crawled_at: datetime
    world_cup_id: int
    thumbnail_url: str
    keywords: list[str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class NewsCreate(NewsBase):
    pass


class NewsResponse(NewsBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)