from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    fifa_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    continent: Mapped[str | None] = mapped_column(String(50), nullable=True)

    players = relationship("Player", back_populates="team")
    champion_world_cups = relationship(
        "WorldCup",
        foreign_keys="[WorldCup.champion_team_id]",
        back_populates="champion_team",
    )
    runner_up_world_cups = relationship(
        "WorldCup",
        foreign_keys="[WorldCup.runner_up_team_id]",
        back_populates="runner_up_team",
    )