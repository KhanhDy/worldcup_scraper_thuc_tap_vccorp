from sqlalchemy.orm import Session

from app.repositories.statistics_repository import StatisticsRepository


class StatisticsService:
    def __init__(self):
        self.repository = StatisticsRepository()

    def get_teams_most_titles(self, db: Session, limit: int = 10):
        return self.repository.get_teams_most_titles(db, limit=limit)

    def get_players_top_scorers(self, db: Session, limit: int = 10):
        return self.repository.get_players_top_scorers(db, limit=limit)

    def get_matches_most_goals(self, db: Session, limit: int = 10):
        rows = self.repository.get_matches_most_goals(db, limit=limit)
        return [
            {
                "match_id": row.match_id,
                "world_cup_id": row.world_cup_id,
                "description": f"{row.team_1_name} vs {row.team_2_name} ({row.stage})",
                "total": row.total,
            }
            for row in rows
        ]

    def get_matches_most_cards(self, db: Session, limit: int = 10):
        rows = self.repository.get_matches_most_cards(db, limit=limit)
        return [
            {
                "match_id": row.match_id,
                "world_cup_id": row.world_cup_id,
                "description": f"{row.team_1_name} vs {row.team_2_name} ({row.stage})",
                "total": row.total,
            }
            for row in rows
        ]

    def get_players_most_appearances(self, db: Session, limit: int = 10):
        return self.repository.get_players_most_appearances(db, limit=limit)
