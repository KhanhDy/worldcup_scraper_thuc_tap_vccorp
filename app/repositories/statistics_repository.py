from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.models.cards import Card
from app.models.goals import Goal
from app.models.matches import Match
from app.models.player import Player
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

    def get_players_top_scorers(self, db: Session, limit: int = 10):
        return (
            db.query(
                Player.id.label("player_id"),
                Player.full_name.label("player_name"),
                func.count(Goal.id).label("total"),
            )
            .join(Goal, Goal.player_id == Player.id)
            .group_by(Player.id, Player.full_name)
            .order_by(func.count(Goal.id).desc(), Player.full_name.asc())
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

    def get_matches_most_cards(self, db: Session, limit: int = 10):
        team_1 = aliased(Team)
        team_2 = aliased(Team)

        return (
            db.query(
                Match.id.label("match_id"),
                Match.world_cup_id.label("world_cup_id"),
                Match.stage.label("stage"),
                team_1.name.label("team_1_name"),
                team_2.name.label("team_2_name"),
                func.count(Card.id).label("total"),
            )
            .join(team_1, team_1.id == Match.team_1_id)
            .join(team_2, team_2.id == Match.team_2_id)
            .join(Card, Card.match_id == Match.id)
            .group_by(Match.id, Match.world_cup_id, Match.stage, team_1.name, team_2.name)
            .order_by(func.count(Card.id).desc(), Match.id.asc())
            .limit(limit)
            .all()
        )

    def get_players_most_appearances(self, db: Session, limit: int = 10):
        goal_events = db.query(
            Goal.player_id.label("player_id"),
            Goal.match_id.label("match_id"),
        )
        card_events = db.query(
            Card.player_id.label("player_id"),
            Card.match_id.label("match_id"),
        )
        appearances = goal_events.union(card_events).subquery()

        return (
            db.query(
                Player.id.label("player_id"),
                Player.full_name.label("player_name"),
                func.count(func.distinct(appearances.c.match_id)).label("total"),
            )
            .join(appearances, appearances.c.player_id == Player.id)
            .group_by(Player.id, Player.full_name)
            .order_by(
                func.count(func.distinct(appearances.c.match_id)).desc(),
                Player.full_name.asc(),
            )
            .limit(limit)
            .all()
        )
