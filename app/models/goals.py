from datetime import datetime

from sqlalchemy import ForeignKey, Integer, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

class Goal(Base):
    __tablename__ = 'goals'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    world_cup_id: Mapped[int] = mapped_column(ForeignKey("world_cups.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    minute: Mapped[int] = mapped_column(Integer, nullable=False)
    extra_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_penalty: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_own_goal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    match = relationship("Match", back_populates="goals")
    world_cup = relationship("WorldCup", back_populates="goals")
    player = relationship("Player", back_populates="goals")
    team = relationship("Team")