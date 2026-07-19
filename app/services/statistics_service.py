from sqlalchemy.orm import Session

from app.repositories.statistics_repository import StatisticsRepository


class StatisticsService:
    def __init__(self):
        self.repository = StatisticsRepository()

    def get_teams_most_titles(self, db: Session):
        return self.repository.get_teams_most_titles(db)

    def get_players_top_scorers(self, db: Session):
        return self.repository.get_players_top_scorers(db)

    def get_matches_most_goals(self, db: Session):
        return self.repository.get_matches_most_goals(db)

    def get_matches_most_cards(self, db: Session):
        return self.repository.get_matches_most_cards(db)

    def get_players_most_appearances(self, db: Session):
        return self.repository.get_players_most_appearances(db)
