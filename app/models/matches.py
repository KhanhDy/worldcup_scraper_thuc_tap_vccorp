from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, DateTime, func
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.database.session import Base
class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    world_cup_id: Mapped[int] = mapped_column(ForeignKey("world_cups.id"), nullable=False)
    team_1_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    team_2_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    group_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    match_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    stadium: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    team_1_score: Mapped[int] = mapped_column(Integer, nullable=False)
    team_2_score: Mapped[int] = mapped_column(Integer, nullable=False)
    team_1_penalty_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team_2_penalty_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    winner_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    world_cup = relationship("WorldCup", back_populates="matches")
    team_1 = relationship("Team", foreign_keys=[team_1_id])
    team_2 = relationship("Team", foreign_keys=[team_2_id])
    winner_team = relationship("Team", foreign_keys=[winner_team_id])

