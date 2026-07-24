from pathlib import Path
from app.crawler.cli import extract_next_data, extract_match_entries, build_team_map
from app.database.session import SessionLocal
from app.models.team import Team
from app.schemas.team import TeamCreate
from app.repositories.team_repository import TeamRepository

html = Path('fifa_matches_page.html').read_text(encoding='utf-8', errors='ignore')
next_data = extract_next_data(html)
matches = extract_match_entries(next_data)
team_map = build_team_map(matches)
print('team_map size', len(team_map))
print('first team', next(iter(team_map.values())))

db = SessionLocal()
repo = TeamRepository()
for team_payload in team_map.values():
    existing = db.query(Team).filter(Team.name == team_payload['name']).first()
    print('existing', team_payload['name'], existing)
    if not existing:
        created = repo.create(db, TeamCreate(name=team_payload['name'], fifa_code=team_payload['fifa_code'], continent=team_payload['continent']))
        print('created', created.id, created.name)
        break

db.commit()
print('count', db.query(Team).count())
db.close()
