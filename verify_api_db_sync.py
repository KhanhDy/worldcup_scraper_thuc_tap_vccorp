from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.world_cup import WorldCup
from app.models.team import Team
from app.models.matches import Match
from app.models.standings import Standing
from app.models.news import News

client = TestClient(app)
db = SessionLocal()


def check(name, cond):
    print(("OK  " if cond else "FAIL"), name)


r = client.get("/teams")
check("/teams status 200", r.status_code == 200)
api_teams = r.json()
db_team_count = db.query(Team).count()
check(f"/teams số lượng khớp DB ({db_team_count})", len(api_teams) == db_team_count)

sample_team = db.query(Team).filter(Team.name == "Brazil").first()
r = client.get(f"/teams/{sample_team.id}")
check("/teams/{id} status 200", r.status_code == 200)
check('/teams/{id} tên đúng "Brazil"', r.json().get("name") == "Brazil")

r = client.get(f"/world-cups")
api_wc = r.json()
db_wc_count = db.query(WorldCup).count()
check(f"/world-cups số lượng khớp DB ({db_wc_count})", len(api_wc) == db_wc_count)

r = client.get(f"/world-cups/year/2018")
data = r.json()
champ_id = db.query(WorldCup).filter(WorldCup.year == 2018).first().champion_team_id
champ_name = db.get(Team, champ_id).name
check("/world-cups/year/2018 status 200", r.status_code == 200)
check(f"/world-cups/year/2018 champion_team_id khớp DB ({champ_name})", data.get("champion_team_id") == champ_id)

wc2018 = db.query(WorldCup).filter(WorldCup.year == 2018).first()
r = client.get(f"/matches/world-cup/{wc2018.id}")
api_matches = r.json()
db_match_count = db.query(Match).filter(Match.world_cup_id == wc2018.id).count()
check(f"/matches/world-cup/{{id}} (WC2018) số lượng khớp DB ({db_match_count})", len(api_matches) == db_match_count)

r = client.get(f"/standings/world-cup/{wc2018.id}/groups/Group%20A")
api_standings = r.json()
db_standing_count = db.query(Standing).filter(
    Standing.world_cup_id == wc2018.id, Standing.group_name == "Group A"
).count()
check(f"/standings .../groups/Group A số lượng khớp DB ({db_standing_count})", len(api_standings) == db_standing_count)

r = client.get(f"/news")
api_news = r.json()
db_news_count = db.query(News).count()
check(f"/news số lượng khớp DB ({db_news_count})", len(api_news) == db_news_count)
if api_news:
    check("/news title giữ đúng tiếng Việt có dấu (không lỗi encoding)", "quyết định VAR" in api_news[0]["title"])
    check("/news keywords là list, giữ đúng dấu tiếng Việt", api_news[0]["keywords"] == ["World Cup 2026", "FIFA", "VAR"])

r = client.get(f"/statistics/teams/most-titles")
top = r.json()
check("/statistics/teams/most-titles trả về Brazil đầu bảng (5 chức VĐ)", top[0]["team_name"] == "Brazil" and top[0]["titles"] == 5)

r = client.get(f"/statistics/matches/most-goals")
check("/statistics/matches/most-goals status 200 + có dữ liệu", r.status_code == 200 and len(r.json()) > 0)

# Test 404 cho id không tồn tại
r = client.get(f"/teams/999999")
check("/teams/999999 trả 404 khi không tồn tại", r.status_code == 404)

db.close()
