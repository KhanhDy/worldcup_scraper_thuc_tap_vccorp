from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cards import Card
from app.models.goals import Goal
from app.models.matches import Match
from app.models.player import Player
from app.models.team import Team
from app.models.world_cup import WorldCup


class StatisticsRepository:
    def get_teams_most_titles(self, db: Session):
        return (
            db.query(
                Team.id.label("team_id"),
                Team.name.label("team_name"),
                func.count(WorldCup.id).label("titles"),
            )
            .join(WorldCup, WorldCup.champion_team_id == Team.id)
            .group_by(Team.id, Team.name)
            .order_by(func.count(WorldCup.id).desc(), Team.name.asc())
            .all()
        )

    def get_players_top_scorers(self, db: Session):
        return (
            db.query(
                Player.id.label("player_id"),
                Player.full_name.label("player_name"),
                func.count(Goal.id).label("total"),
            )
            .join(Goal, Goal.player_id == Player.id)
            .group_by(Player.id, Player.full_name)
            .order_by(func.count(Goal.id).desc(), Player.full_name.asc())
            .all()
        )

    def get_matches_most_goals(self, db: Session):
        return (
            db.query(
                Match.id.label("match_id"),
                Match.world_cup_id.label("world_cup_id"),
                (Match.team_1_score + Match.team_2_score).label("total"),
            )
            .order_by((Match.team_1_score + Match.team_2_score).desc(), Match.id.asc())
            .all()
        )

    def get_matches_most_cards(self, db: Session):
        return (
            db.query(
                Match.id.label("match_id"),
                Match.world_cup_id.label("world_cup_id"),
                func.count(Card.id).label("total"),
            )
            .join(Card, Card.match_id == Match.id)
            .group_by(Match.id, Match.world_cup_id)
            .order_by(func.count(Card.id).desc(), Match.id.asc())
            .all()
        )

    def get_players_most_appearances(self, db: Session):
        return (
            db.query(
                Player.id.label("player_id"),
                Player.full_name.label("player_name"),
                func.count(func.distinct(Goal.match_id)).label("total"),
            )
            .join(Goal, Goal.player_id == Player.id)
            .group_by(Player.id, Player.full_name)
            .order_by(func.count(func.distinct(Goal.match_id)).desc(), Player.full_name.asc())
            .all()
        )
