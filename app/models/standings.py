from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

class Standing(Base):
    __tablename__ = "standings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    world_cup_id: Mapped[int] = mapped_column(ForeignKey("world_cups.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    group_name: Mapped[str] = mapped_column(String(50), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    played: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False)
    draws: Mapped[int] = mapped_column(Integer, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, nullable=False)
    goals_for: Mapped[int] = mapped_column(Integer, nullable=False)
    goals_against: Mapped[int] = mapped_column(Integer, nullable=False)
    goal_difference: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    qualified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    world_cup = relationship("WorldCup", back_populates="standings")
    team = relationship("Team")