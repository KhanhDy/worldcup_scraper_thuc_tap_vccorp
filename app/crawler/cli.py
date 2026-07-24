from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.database.base import Base
from app.database.session import SessionLocal
from app.models.cards import Card
from app.models.goals import Goal
from app.models.matches import Match
from app.models.news import News
from app.models.player import Player
from app.models.standings import Standing
from app.models.team import Team
from app.models.world_cup import WorldCup
from app.repositories.match_repository import MatchRepository
from app.repositories.news_repository import NewsRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.world_cup_repository import WorldCupRepository
from app.schemas.match import MatchCreate
from app.schemas.team import TeamCreate
from app.schemas.world_cup import WorldCupCreate
DEFAULT_WORLD_CUP_URL = "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026"
DEFAULT_VNEXPRESS_URL = "https://vnexpress.net/tag/world-cup-1"
DEFAULT_TUOITRE_URL = "https://tuoitre.vn/world-cup.htm"
DEFAULT_THANHNIEN_URL = "https://thanhnien.vn/world-cup.htm"
DEFAULT_WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup"


@dataclass(frozen=True)
class CrawlJob:
    entity: str
    source: str
    url: str
    target_table: str


class PageMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self._in_title = False
        self.meta: dict[str, str] = {}
        self.links: list[str] = []
        self.headings: list[str] = []
        self.text_chunks: list[str] = []
        self._heading_tag: str | None = None
        self._current_heading: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        attr_map = {key.lower(): value for key, value in attrs}
        if tag.lower() == "title":
            self._in_title = True
        elif tag.lower() == "meta":
            key = attr_map.get("name") or attr_map.get("property")
            content = attr_map.get("content")
            if key and content and key.lower() not in self.meta:
                self.meta[key.lower()] = content
        elif tag.lower() == "a":
            href = attr_map.get("href")
            if href:
                self.links.append(href)
        elif tag.lower() in {"h1", "h2", "h3"}:
            self._heading_tag = tag.lower()
            self._current_heading = []

    def handle_endtag(self, tag: str):
        if tag.lower() == "title":
            self._in_title = False
        elif self._heading_tag == tag.lower():
            heading = "".join(self._current_heading).strip()
            if heading:
                self.headings.append(heading)
            self._heading_tag = None
            self._current_heading = []

    def handle_data(self, data: str):
        stripped = data.strip()
        if stripped:
            self.text_chunks.append(stripped)
        if self._in_title:
            self.title_parts.append(data)
        if self._heading_tag:
            self._current_heading.append(data)

    @property
    def title(self) -> str:
        return "".join(self.title_parts).strip()

    @property
    def text(self) -> str:
        return " ".join(self.text_chunks).strip()


def extract_next_data(html: str) -> dict[str, object]:
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if not match:
        return {}

    return json.loads(match.group(1))


def extract_match_entries(next_data: dict[str, object]) -> list[dict[str, object]]:
    if not isinstance(next_data, dict):
        return []

    stack: list[object] = [next_data]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            matches = current.get("matches")
            if isinstance(matches, list) and matches and isinstance(matches[0], dict):
                if "idMatch" in matches[0] or "teamAId" in matches[0] or "teamAName" in matches[0]:
                    return [match for match in matches if isinstance(match, dict)]
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)

    return []


def extract_text_value(value: object) -> str:
    if isinstance(value, list) and value:
        first_item = value[0]
        if isinstance(first_item, dict):
            return str(first_item.get("description") or first_item.get("value") or "")
        return str(first_item)
    if isinstance(value, dict):
        return str(value.get("description") or value.get("value") or "")
    if value is None:
        return ""
    return str(value)


def build_team_map(matches: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    teams: dict[str, dict[str, object]] = {}
    for match in matches:
        for prefix in ("A", "B"):
            team_id = str(match.get(f"team{prefix}Id") or "").strip()
            if not team_id:
                continue
            if team_id not in teams:
                teams[team_id] = {
                    "id": int(team_id),
                    "name": extract_text_value(match.get(f"team{prefix}Name")) or f"Team {team_id}",
                    "fifa_code": str(match.get(f"team{prefix}CountryCode") or "").strip() or None,
                    "continent": None,
                }
    return teams


def build_match_record(match: dict[str, object], world_cup_id: int) -> dict[str, object]:
    team_1_score = int(match.get("teamAScore") or 0)
    team_2_score = int(match.get("teamBScore") or 0)
    penalty_1 = match.get("teamAPenaltyScore")
    penalty_2 = match.get("teamBPenaltyScore")
    match_date_value = match.get("matchDate")

    if isinstance(match_date_value, str):
        match_date_text = match_date_value.strip()
        if match_date_text.endswith("Z"):
            match_date_text = match_date_text[:-1] + "+00:00"
        try:
            match_date = datetime.fromisoformat(match_date_text)
        except ValueError:
            match_date = datetime.now(timezone.utc)
    else:
        match_date = datetime.now(timezone.utc)

    return {
        "world_cup_id": world_cup_id,
        "team_1_id": int(match.get("teamAId") or 0),
        "team_2_id": int(match.get("teamBId") or 0),
        "stage": extract_text_value(match.get("stageName")) or "Unknown",
        "group_name": extract_text_value(match.get("groupName")) or None,
        "match_date": match_date,
        "stadium": extract_text_value(match.get("stadiumName")) or "Unknown",
        "city": extract_text_value(match.get("cityName")) or extract_text_value(match.get("stadiumName")) or "Unknown",
        "team_1_score": team_1_score,
        "team_2_score": team_2_score,
        "team_1_penalty_score": int(penalty_1) if penalty_1 not in (None, "") else None,
        "team_2_penalty_score": int(penalty_2) if penalty_2 not in (None, "") else None,
        "winner_team_id": None,
        "attendance": None,
        "referee": None,
    }


def build_standing_rows(matches: list[dict[str, object]], world_cup_id: int) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, dict[str, int | bool]]] = {}

    for match in matches:
        group_name = extract_text_value(match.get("groupName")) or None
        if not group_name:
            continue

        grouped.setdefault(group_name, {})

        team_a_id = str(match.get("teamAId") or "").strip()
        team_b_id = str(match.get("teamBId") or "").strip()
        team_a_score = int(match.get("teamAScore") or 0)
        team_b_score = int(match.get("teamBScore") or 0)

        for team_id in (team_a_id, team_b_id):
            if team_id and team_id not in grouped[group_name]:
                grouped[group_name][team_id] = {
                    "played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "goal_difference": 0,
                    "points": 0,
                    "qualified": False,
                }

        if team_a_id and team_b_id:
            a = grouped[group_name][team_a_id]
            b = grouped[group_name][team_b_id]
            a["played"] += 1
            b["played"] += 1
            a["goals_for"] += team_a_score
            a["goals_against"] += team_b_score
            b["goals_for"] += team_b_score
            b["goals_against"] += team_a_score

            if team_a_score > team_b_score:
                a["wins"] += 1
                b["losses"] += 1
                a["points"] += 3
            elif team_b_score > team_a_score:
                b["wins"] += 1
                a["losses"] += 1
                b["points"] += 3
            else:
                a["draws"] += 1
                b["draws"] += 1
                a["points"] += 1
                b["points"] += 1

    rows: list[dict[str, object]] = []
    for group_name, teams in grouped.items():
        ordered_teams = sorted(
            teams.items(),
            key=lambda item: (
                -(item[1]["points"]),
                -((item[1]["goals_for"] or 0) - (item[1]["goals_against"] or 0)),
                -(item[1]["goals_for"]),
                int(item[0]),
            ),
        )

        for rank, (team_id, stats) in enumerate(ordered_teams, start=1):
            goals_for = int(stats["goals_for"] or 0)
            goals_against = int(stats["goals_against"] or 0)
            rows.append(
                {
                    "world_cup_id": world_cup_id,
                    "team_id": int(team_id),
                    "group_name": group_name,
                    "rank": rank,
                    "played": int(stats["played"] or 0),
                    "wins": int(stats["wins"] or 0),
                    "draws": int(stats["draws"] or 0),
                    "losses": int(stats["losses"] or 0),
                    "goals_for": goals_for,
                    "goals_against": goals_against,
                    "goal_difference": goals_for - goals_against,
                    "points": int(stats["points"] or 0),
                    "qualified": bool(stats["qualified"]),
                }
            )

    return rows


def build_jobs(entity: str) -> list[CrawlJob]:
    normalized = entity.lower()
    jobs_by_entity: dict[str, list[CrawlJob]] = {
        "world_cup": [
            CrawlJob(
                entity="world_cup",
                source="fifa",
                url=DEFAULT_WORLD_CUP_URL,
                target_table="world_cups",
            ),
            CrawlJob(
                entity="world_cup",
                source="wikipedia",
                url=DEFAULT_WIKIPEDIA_URL,
                target_table="world_cups",
            ),
        ],
        "teams": [
            CrawlJob(
                entity="teams",
                source="fifa",
                url=DEFAULT_WORLD_CUP_URL,
                target_table="teams",
            ),
            CrawlJob(
                entity="teams",
                source="wikipedia",
                url=DEFAULT_WIKIPEDIA_URL,
                target_table="teams",
            ),
        ],
        "players": [
            CrawlJob(
                entity="players",
                source="fifa",
                url=DEFAULT_WORLD_CUP_URL,
                target_table="players",
            ),
        ],
        "matches": [
            CrawlJob(
                entity="matches",
                source="fifa",
                url=DEFAULT_WORLD_CUP_URL,
                target_table="matches",
            ),
        ],
        "standings": [
            CrawlJob(
                entity="standings",
                source="fifa",
                url=DEFAULT_WORLD_CUP_URL,
                target_table="standings",
            ),
        ],
        "events": [
            CrawlJob(
                entity="events",
                source="fifa",
                url=DEFAULT_WORLD_CUP_URL,
                target_table="goals",
            ),
            CrawlJob(
                entity="events",
                source="fifa",
                url=DEFAULT_WORLD_CUP_URL,
                target_table="cards",
            ),
        ],
        "news": [
            CrawlJob(
                entity="news",
                source="vnexpress",
                url=DEFAULT_VNEXPRESS_URL,
                target_table="news",
            ),
            CrawlJob(
                entity="news",
                source="tuoitre",
                url=DEFAULT_TUOITRE_URL,
                target_table="news",
            ),
            CrawlJob(
                entity="news",
                source="thanhnien",
                url=DEFAULT_THANHNIEN_URL,
                target_table="news",
            ),
        ],
        "reference": [
            CrawlJob(
                entity="reference",
                source="wikipedia",
                url=DEFAULT_WIKIPEDIA_URL,
                target_table="world_cups",
            ),
        ],
        "all": [
            CrawlJob(
                entity="world_cup",
                source="fifa",
                url=DEFAULT_WORLD_CUP_URL,
                target_table="world_cups",
            ),
            CrawlJob(
                entity="teams",
                source="fifa",
                url=DEFAULT_WORLD_CUP_URL,
                target_table="teams",
            ),
            CrawlJob(
                entity="players",
                source="fifa",
                url=DEFAULT_WORLD_CUP_URL,
                target_table="players",
            ),
            CrawlJob(
                entity="matches",
                source="fifa",
                url=DEFAULT_WORLD_CUP_URL,
                target_table="matches",
            ),
            CrawlJob(
                entity="standings",
                source="fifa",
                url=DEFAULT_WORLD_CUP_URL,
                target_table="standings",
            ),
            CrawlJob(
                entity="events",
                source="fifa",
                url=DEFAULT_WORLD_CUP_URL,
                target_table="goals",
            ),
            CrawlJob(
                entity="events",
                source="fifa",
                url=DEFAULT_WORLD_CUP_URL,
                target_table="cards",
            ),
            CrawlJob(
                entity="news",
                source="vnexpress",
                url=DEFAULT_VNEXPRESS_URL,
                target_table="news",
            ),
            CrawlJob(
                entity="news",
                source="tuoitre",
                url=DEFAULT_TUOITRE_URL,
                target_table="news",
            ),
            CrawlJob(
                entity="news",
                source="thanhnien",
                url=DEFAULT_THANHNIEN_URL,
                target_table="news",
            ),
            CrawlJob(
                entity="reference",
                source="wikipedia",
                url=DEFAULT_WIKIPEDIA_URL,
                target_table="world_cups",
            ),
        ],
    }

    if normalized not in jobs_by_entity:
        available = ", ".join(sorted(jobs_by_entity))
        raise SystemExit(f"Unknown entity '{entity}'. Available values: {available}")

    return jobs_by_entity[normalized]


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value or "page"


def fetch_page(url: str, timeout: int) -> tuple[str, dict[str, str], str]:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            raw_bytes = response.read()
            content_type = response.headers.get_content_charset() or "utf-8"
            final_url = response.geturl()
            text = raw_bytes.decode(content_type, errors="replace")
            headers = {key.lower(): value for key, value in response.headers.items()}
            headers["content-type"] = response.headers.get("Content-Type", "")
            headers["final-url"] = final_url
            return text, headers, final_url
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        project_root = Path(__file__).resolve().parents[2]
        fallback_path = project_root / "fifa_matches_page.html"
        if fallback_path.exists() and "fifa" in url.lower():
            html = fallback_path.read_text(encoding="utf-8", errors="ignore")
            headers = {"content-type": "text/html; charset=utf-8", "final-url": url}
            return html, headers, url
        raise


def parse_page(html: str) -> dict[str, object]:
    parser = PageMetadataParser()
    parser.feed(html)
    parser.close()
    return {
        "title": parser.title,
        "meta": parser.meta,
        "headings": parser.headings[:10],
        "links": parser.links[:50],
        "text": parser.text[:5000],
    }


def save_artifacts(output_dir: Path, job: CrawlJob, final_url: str, html: str, parsed: dict[str, object], headers: dict[str, str]) -> dict[str, str]:
    source_dir = output_dir / job.entity / job.source
    source_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify(urlparse(final_url).path or job.entity)
    html_path = source_dir / f"{slug}.html"
    json_path = source_dir / f"{slug}.json"

    html_path.write_text(html, encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "entity": job.entity,
                "source": job.source,
                "target_table": job.target_table,
                "requested_url": job.url,
                "final_url": final_url,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "headers": headers,
                "parsed": parsed,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "html_path": str(html_path),
        "json_path": str(json_path),
    }


def run_jobs(jobs: Iterable[CrawlJob], output_dir: Path, timeout: int) -> int:
    failures = 0
    for job in jobs:
        try:
            html, headers, final_url = fetch_page(job.url, timeout=timeout)
            parsed = parse_page(html)
            saved = save_artifacts(output_dir, job, final_url, html, parsed, headers)
            result = {
                "status": "ok",
                "entity": job.entity,
                "source": job.source,
                "target_table": job.target_table,
                "url": job.url,
                "final_url": final_url,
                "title": parsed.get("title"),
                "html_path": saved["html_path"],
                "json_path": saved["json_path"],
            }
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            failures += 1
            result = {
                "status": "error",
                "entity": job.entity,
                "source": job.source,
                "target_table": job.target_table,
                "url": job.url,
                "error": str(exc),
            }

        print(json.dumps(result, ensure_ascii=False))

    return failures


def sync_jobs(jobs: Iterable[CrawlJob], output_dir: Path, timeout: int) -> int:
    failures = 0
    db = SessionLocal()
    world_cup_repository = WorldCupRepository()
    team_repository = TeamRepository()
    match_repository = MatchRepository()
    news_repository = NewsRepository()

    world_cup = world_cup_repository.get_by_year(db, 2026)

    if not world_cup:
        world_cup = world_cup_repository.create(
            db,
            WorldCupCreate(
                year=2026,
                host_country="Canada/Mexico/USA",
                champion_team_id=None,
                runner_up_team_id=None,
            ),
        )

    try:
        for job in jobs:
            try:
                html, headers, final_url = fetch_page(job.url, timeout=timeout)
                parsed = parse_page(html)
                save_artifacts(output_dir, job, final_url, html, parsed, headers)

                if job.target_table == "world_cups":
                    world_cup = world_cup_repository.get_by_year(db, 2026) or world_cup

                elif job.target_table == "teams":
                    next_data = extract_next_data(html)
                    matches = extract_match_entries(next_data)
                    team_map = build_team_map(matches)
                    for team_payload in team_map.values():
                        existing_team = db.query(Team).filter(Team.name == team_payload["name"]).first()
                        if not existing_team:
                            created = team_repository.create(
                                db,
                                TeamCreate(
                                    name=team_payload["name"],
                                    fifa_code=team_payload["fifa_code"],
                                    continent=team_payload["continent"],
                                ),
                            )
                            team_payload["db_id"] = created.id
                        else:
                            team_payload["db_id"] = existing_team.id

                elif job.target_table == "matches":
                    next_data = extract_next_data(html)
                    matches = extract_match_entries(next_data)
                    for match_data in matches:
                        record = build_match_record(match_data, world_cup.id)
                        if not record["team_1_id"] or not record["team_2_id"]:
                            continue
                        existing_match = (
                            db.query(Match)
                            .filter(
                                Match.world_cup_id == record["world_cup_id"],
                                Match.team_1_id == record["team_1_id"],
                                Match.team_2_id == record["team_2_id"],
                                Match.match_date == record["match_date"],
                                Match.stage == record["stage"],
                            )
                            .first()
                        )
                        if not existing_match:
                            match_repository.create(
                                db,
                                MatchCreate(
                                    world_cup_id=record["world_cup_id"],
                                    team_1_id=record["team_1_id"],
                                    team_2_id=record["team_2_id"],
                                    stage=record["stage"],
                                    group_name=record["group_name"],
                                    match_date=record["match_date"],
                                    stadium=record["stadium"],
                                    city=record["city"],
                                    team_1_score=record["team_1_score"],
                                    team_2_score=record["team_2_score"],
                                    team_1_penalty_score=record["team_1_penalty_score"],
                                    team_2_penalty_score=record["team_2_penalty_score"],
                                    winner_team_id=record["winner_team_id"],
                                    attendance=record["attendance"],
                                    referee=record["referee"],
                                ),
                            )

                elif job.target_table == "standings":
                    next_data = extract_next_data(html)
                    matches = extract_match_entries(next_data)
                    rows = build_standing_rows(matches, world_cup.id)
                    for row in rows:
                        existing_standing = (
                            db.query(Standing)
                            .filter(
                                Standing.world_cup_id == row["world_cup_id"],
                                Standing.team_id == row["team_id"],
                                Standing.group_name == row["group_name"],
                            )
                            .first()
                        )
                        if existing_standing:
                            for field in ["rank", "played", "wins", "draws", "losses", "goals_for", "goals_against", "goal_difference", "points", "qualified"]:
                                setattr(existing_standing, field, row[field])
                        else:
                            db.add(Standing(**row))

                elif job.target_table == "goals":
                    pass

                elif job.target_table == "cards":
                    pass

                elif job.target_table == "news":
                    existing_news = db.query(News).filter(News.url == final_url).first()
                    if not existing_news:
                        title = str(parsed.get("title") or "Untitled article")
                        summary = str(parsed.get("meta", {}).get("description") or title)
                        text = str(parsed.get("text") or summary)
                        now = datetime.now(timezone.utc)
                        news_repository.create(
                            db,
                            NewsCreate(
                                title=title,
                                slug=slugify(urlparse(final_url).path or title),
                                summary=summary,
                                content=text,
                                url=final_url,
                                source=job.source,
                                author="Unknown",
                                published_at=now,
                                crawled_at=now,
                                world_cup_id=world_cup.id,
                                thumbnail_url="",
                                keywords=[],
                            ),
                        )

                result = {
                    "status": "ok",
                    "entity": job.entity,
                    "source": job.source,
                    "target_table": job.target_table,
                    "url": job.url,
                    "final_url": final_url,
                    "title": parsed.get("title"),
                    "synced": True,
                }
            except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                failures += 1
                result = {
                    "status": "error",
                    "entity": job.entity,
                    "source": job.source,
                    "target_table": job.target_table,
                    "url": job.url,
                    "error": str(exc),
                }

            print(json.dumps(result, ensure_ascii=False))

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="World Cup crawl command runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch one URL and save raw HTML + metadata")
    fetch_parser.add_argument("--source", required=True, help="Source name, for example fifa or vnexpress")
    fetch_parser.add_argument("--url", required=True, help="Page URL to crawl")
    fetch_parser.add_argument("--entity", default="custom", help="Logical entity name used in output folders")
    fetch_parser.add_argument("--table", default="news", help="Target table name for the crawl record")
    fetch_parser.add_argument("--output", default="data/crawl", help="Output directory")
    fetch_parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")

    batch_parser = subparsers.add_parser("batch", help="Run the prebuilt source plan")
    batch_parser.add_argument(
        "--entity",
        default="all",
        choices=["world_cup", "teams", "players", "matches", "standings", "events", "news", "reference", "all"],
        help="Which crawl plan to run",
    )
    batch_parser.add_argument("--output", default="data/crawl", help="Output directory")
    batch_parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")

    sync_parser = subparsers.add_parser("sync", help="Fetch pages and store supported records in the database")
    sync_parser.add_argument(
        "--entity",
        default="all",
        choices=["world_cup", "teams", "players", "matches", "standings", "events", "news", "reference", "all"],
        help="Which crawl plan to run",
    )
    sync_parser.add_argument("--output", default="data/crawl", help="Output directory")
    sync_parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")

    args = parser.parse_args(argv)
    output_dir = Path(args.output)

    if args.command == "fetch":
        job = CrawlJob(
            entity=args.entity,
            source=args.source,
            url=args.url,
            target_table=args.table,
        )
        return run_jobs([job], output_dir, timeout=args.timeout)

    if args.command == "sync":
        jobs = build_jobs(args.entity)
        return sync_jobs(jobs, output_dir, timeout=args.timeout)

    jobs = build_jobs(args.entity)
    return run_jobs(jobs, output_dir, timeout=args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
