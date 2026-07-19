from datetime import datetime

from sqlalchemy import ForeignKey, String, DateTime, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    crawled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    world_cup_id: Mapped[int] = mapped_column(ForeignKey("world_cups.id"), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=False)
    keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    world_cup = relationship("WorldCup", back_populates="news")