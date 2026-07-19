from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class WorldCup(Base):
    __tablename__ = "world_cups"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    host_country: Mapped[str] = mapped_column(String(100), nullable=False)
    champion_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    runner_up_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)

    champion_team = relationship(
        "Team",
        foreign_keys=[champion_team_id],
        back_populates="champion_world_cups",
    )
    runner_up_team = relationship(
        "Team",
        foreign_keys=[runner_up_team_id],
        back_populates="runner_up_world_cups",
    )
    matches = relationship("Match", back_populates="world_cup")
    standings = relationship("Standing", back_populates="world_cup")
    goals = relationship("Goal", back_populates="world_cup")
    cards = relationship("Card", back_populates="world_cup")
    news = relationship("News", back_populates="world_cup")