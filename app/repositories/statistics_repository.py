from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.models.matches import Match
from app.models.team import Team
from app.models.world_cup import WorldCup


class StatisticsRepository:
    def get_teams_most_titles(self, db: Session, limit: int = 10):
        return (
            db.query(
                Team.id.label("team_id"),
                Team.name.label("team_name"),
                func.count(WorldCup.id).label("titles"),
            )
            .join(WorldCup, WorldCup.champion_team_id == Team.id)
            .group_by(Team.id, Team.name)
            .order_by(func.count(WorldCup.id).desc(), Team.name.asc())
            .limit(limit)
            .all()
        )

    def get_matches_most_goals(self, db: Session, limit: int = 10):
        team_1 = aliased(Team)
        team_2 = aliased(Team)

        return (
            db.query(
                Match.id.label("match_id"),
                Match.world_cup_id.label("world_cup_id"),
                Match.stage.label("stage"),
                team_1.name.label("team_1_name"),
                team_2.name.label("team_2_name"),
                (Match.team_1_score + Match.team_2_score).label("total"),
            )
            .join(team_1, team_1.id == Match.team_1_id)
            .join(team_2, team_2.id == Match.team_2_id)
            .order_by((Match.team_1_score + Match.team_2_score).desc(), Match.id.asc())
            .limit(limit)
            .all()
        )
