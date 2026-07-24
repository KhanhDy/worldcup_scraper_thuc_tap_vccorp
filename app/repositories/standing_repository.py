from sqlalchemy.orm import Session

from app.models.standings import Standing
from app.models.team import Team


class StandingRepository:
    def get_by_world_cup(self, db: Session, world_cup_id: int):
        return (
            db.query(
                Standing.id.label("id"),
                Standing.world_cup_id.label("world_cup_id"),
                Standing.team_id.label("team_id"),
                Team.name.label("team_name"),
                Standing.group_name.label("group_name"),
                Standing.rank.label("rank"),
                Standing.played.label("played"),
                Standing.wins.label("wins"),
                Standing.draws.label("draws"),
                Standing.losses.label("losses"),
                Standing.goals_for.label("goals_for"),
                Standing.goals_against.label("goals_against"),
                Standing.goal_difference.label("goal_difference"),
                Standing.points.label("points"),
                Standing.qualified.label("qualified"),
                Standing.created_at.label("created_at"),
                Standing.updated_at.label("updated_at"),
            )
            .join(Team, Team.id == Standing.team_id)
            .filter(Standing.world_cup_id == world_cup_id)
            .order_by(Standing.group_name.asc(), Standing.rank.asc(), Team.name.asc())
            .all()
        )

    def get_by_world_cup_group(self, db: Session, world_cup_id: int, group_name: str):
        return (
            db.query(
                Standing.id.label("id"),
                Standing.world_cup_id.label("world_cup_id"),
                Standing.team_id.label("team_id"),
                Team.name.label("team_name"),
                Standing.group_name.label("group_name"),
                Standing.rank.label("rank"),
                Standing.played.label("played"),
                Standing.wins.label("wins"),
                Standing.draws.label("draws"),
                Standing.losses.label("losses"),
                Standing.goals_for.label("goals_for"),
                Standing.goals_against.label("goals_against"),
                Standing.goal_difference.label("goal_difference"),
                Standing.points.label("points"),
                Standing.qualified.label("qualified"),
                Standing.created_at.label("created_at"),
                Standing.updated_at.label("updated_at"),
            )
            .join(Team, Team.id == Standing.team_id)
            .filter(
                Standing.world_cup_id == world_cup_id,
                Standing.group_name == group_name,
            )
            .order_by(Standing.rank.asc(), Team.name.asc())
            .all()
        )
