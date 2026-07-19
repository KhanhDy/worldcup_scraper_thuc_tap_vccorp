from datetime import date

from sqlalchemy import String, ForeignKey, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
class Player(Base):
    __tablename__ = 'players'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    position: Mapped[str | None] = mapped_column(String(50), nullable=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)

    team = relationship("Team", back_populates="players")
    goals = relationship("Goal", back_populates="player")
    cards = relationship("Card", back_populates="player")