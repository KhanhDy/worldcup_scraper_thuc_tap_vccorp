"""
CLI đồng bộ dữ liệu Trận đấu / Bảng xếp hạng lịch sử World Cup (1930-nay)
từ nguồn mở openfootball/worldcup.json vào database của dự án.

Cách chạy (từ thư mục gốc project, đã kích hoạt venv):

    # Đồng bộ toàn bộ các kỳ, tải trực tiếp qua HTTP (raw.githubusercontent.com)
    python -m app.crawler.sync_openfootball --years all

    # Chỉ vài năm cụ thể
    python -m app.crawler.sync_openfootball --years 2014,2018,2022

    # Một khoảng năm
    python -m app.crawler.sync_openfootball --years 1990-2010

    # Xem trước sẽ ghi gì mà KHÔNG đụng vào DB
    python -m app.crawler.sync_openfootball --years 2018 --dry-run

    # Dùng bản clone local của repo openfootball (nhanh, không cần mạng mỗi lần)
    #   git clone https://github.com/openfootball/worldcup.json.git .openfootball_cache
    python -m app.crawler.sync_openfootball --years all --local-repo .openfootball_cache
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

from app.crawler.sources.openfootball_source import (
    HOST_COUNTRIES,
    WORLD_CUP_YEARS,
    YearBundle,
    build_match_payloads,
    build_standing_payloads,
    build_team_payloads,
    build_world_cup_payload,
    fetch_year_bundle,
)


def parse_years_arg(raw: str) -> list[int]:
    if raw.strip().lower() == "all":
        return list(WORLD_CUP_YEARS)

    years: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start_str, end_str = chunk.split("-", 1)
            start, end = int(start_str), int(end_str)
            years.extend(y for y in WORLD_CUP_YEARS if start <= y <= end)
        else:
            years.append(int(chunk))

    unknown = sorted(set(years) - set(WORLD_CUP_YEARS))
    if unknown:
        raise SystemExit(
            f"Năm không hợp lệ / World Cup không tổ chức: {unknown}. "
            f"Các năm hợp lệ: {WORLD_CUP_YEARS}"
        )
    return sorted(set(years))


def sync_year(db, bundle: YearBundle, stats: dict[str, int]) -> None:
    # Import muộn để đảm bảo DATABASE_URL override (nếu có) đã được set trước
    # khi app.database.session tạo engine.
    from app.models.matches import Match
    from app.models.standings import Standing
    from app.models.team import Team
    from app.models.world_cup import WorldCup
    from app.repositories.team_repository import TeamRepository
    from app.repositories.world_cup_repository import WorldCupRepository
    from app.schemas.team import TeamCreate
    from app.schemas.world_cup import WorldCupCreate

    world_cup_repository = WorldCupRepository()
    team_repository = TeamRepository()

    # 1) World Cup -----------------------------------------------------
    wc_payload = build_world_cup_payload(bundle.year)
    world_cup = world_cup_repository.get_by_year(db, bundle.year)
    if not world_cup:
        world_cup = world_cup_repository.create(
            db,
            WorldCupCreate(
                year=wc_payload["year"],
                host_country=wc_payload["host_country"],
                champion_team_id=None,
                runner_up_team_id=None,
            ),
        )
        stats["world_cups_created"] += 1

    # 2) Teams -----------------------------------------------------------
    team_name_to_id: dict[str, int] = {}
    for team_payload in build_team_payloads(bundle):
        existing = db.query(Team).filter(Team.name == team_payload["name"]).first()
        if existing:
            team_name_to_id[team_payload["name"]] = existing.id
            continue
        created = team_repository.create(
            db,
            TeamCreate(
                name=team_payload["name"],
                fifa_code=team_payload["fifa_code"],
                continent=team_payload["continent"],
            ),
        )
        team_name_to_id[team_payload["name"]] = created.id
        stats["teams_created"] += 1

    # 3) Matches -----------------------------------------------------------
    final_match_winner_loser: Optional[tuple[int, int]] = None  # (champion_id, runner_up_id)

    for match_payload in build_match_payloads(bundle):
        team_1_id = team_name_to_id.get(match_payload["team_1_name"])
        team_2_id = team_name_to_id.get(match_payload["team_2_name"])
        if not team_1_id or not team_2_id:
            stats["matches_skipped_unknown_team"] += 1
            continue

        existing_match = (
            db.query(Match)
            .filter(
                Match.world_cup_id == world_cup.id,
                Match.team_1_id == team_1_id,
                Match.team_2_id == team_2_id,
                Match.match_date == match_payload["match_date"],
                Match.stage == match_payload["stage"],
            )
            .first()
        )

        winner_team_id = None
        if match_payload["winner"] == "team1":
            winner_team_id = team_1_id
        elif match_payload["winner"] == "team2":
            winner_team_id = team_2_id

        if match_payload["stage"] == "Final" and winner_team_id:
            loser_team_id = team_2_id if winner_team_id == team_1_id else team_1_id
            final_match_winner_loser = (winner_team_id, loser_team_id)

        if existing_match:
            match_row = existing_match
            match_row.team_1_score = match_payload["team_1_score"]
            match_row.team_2_score = match_payload["team_2_score"]
            match_row.team_1_penalty_score = match_payload["team_1_penalty_score"]
            match_row.team_2_penalty_score = match_payload["team_2_penalty_score"]
            match_row.winner_team_id = winner_team_id
            match_row.stadium = match_payload["stadium"]
            match_row.city = match_payload["city"]
            match_row.group_name = match_payload["group_name"]
            stats["matches_updated"] += 1
        else:
            match_row = Match(
                world_cup_id=world_cup.id,
                team_1_id=team_1_id,
                team_2_id=team_2_id,
                stage=match_payload["stage"],
                group_name=match_payload["group_name"],
                match_date=match_payload["match_date"],
                stadium=match_payload["stadium"],
                city=match_payload["city"],
                team_1_score=match_payload["team_1_score"],
                team_2_score=match_payload["team_2_score"],
                team_1_penalty_score=match_payload["team_1_penalty_score"],
                team_2_penalty_score=match_payload["team_2_penalty_score"],
                winner_team_id=winner_team_id,
            )
            db.add(match_row)
            db.flush()
            stats["matches_created"] += 1

    # 4) Standings -----------------------------------------------------------
    final_round_group_ranks: dict[int, int] = {}  # rank -> team_id, cho ca "Final Round" kiểu WC1950

    for row in build_standing_payloads(bundle):
        team_id = team_name_to_id.get(row["team_name"])
        if not team_id:
            continue
        if row["group_name"] == "Final Round" and row["rank"] in (1, 2):
            final_round_group_ranks[row["rank"]] = team_id

        existing_standing = (
            db.query(Standing)
            .filter(
                Standing.world_cup_id == world_cup.id,
                Standing.team_id == team_id,
                Standing.group_name == row["group_name"],
            )
            .first()
        )
        payload = {
            "rank": row["rank"],
            "played": row["played"],
            "wins": row["wins"],
            "draws": row["draws"],
            "losses": row["losses"],
            "goals_for": row["goals_for"],
            "goals_against": row["goals_against"],
            "goal_difference": row["goal_difference"],
            "points": row["points"],
            "qualified": row["qualified"],
        }
        if existing_standing:
            for field, value in payload.items():
                setattr(existing_standing, field, value)
            stats["standings_updated"] += 1
        else:
            db.add(
                Standing(
                    world_cup_id=world_cup.id,
                    team_id=team_id,
                    group_name=row["group_name"],
                    **payload,
                )
            )
            stats["standings_created"] += 1

    # 5) Vô địch / Á quân -----------------------------------------------------
    # Ưu tiên trận có stage == "Final". Riêng WC1950 không có trận "Final"
    # (quyết định bằng vòng tròn tính điểm 4 đội) -> suy ra từ hạng 1/2 của
    # BXH "Final Round" vừa tính ở bước 4.
    if not final_match_winner_loser and 1 in final_round_group_ranks and 2 in final_round_group_ranks:
        final_match_winner_loser = (final_round_group_ranks[1], final_round_group_ranks[2])

    if final_match_winner_loser:
        champion_id, runner_up_id = final_match_winner_loser
        if world_cup.champion_team_id != champion_id or world_cup.runner_up_team_id != runner_up_id:
            world_cup.champion_team_id = champion_id
            world_cup.runner_up_team_id = runner_up_id
            stats["world_cups_updated"] += 1


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Đồng bộ dữ liệu World Cup lịch sử từ openfootball/worldcup.json")
    parser.add_argument("--years", default="all", help="'all', '2018,2022' hoặc khoảng '1990-2010'")
    parser.add_argument("--local-repo", default=None, help="Đường dẫn thư mục đã git clone openfootball/worldcup.json")
    parser.add_argument("--db-url", default=None, help="Ghi đè DATABASE_URL (mặc định lấy từ app/.env)")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in ra số liệu, không ghi DB")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout (giây) khi tải qua mạng")
    args = parser.parse_args(argv)

    if args.db_url:
        os.environ["DATABASE_URL"] = args.db_url

    years = parse_years_arg(args.years)
    local_repo_root = Path(args.local_repo) if args.local_repo else None

    print(f"[openfootball-sync] Sẽ xử lý {len(years)} kỳ World Cup: {years}")

    if args.dry_run:
        for year in years:
            bundle = fetch_year_bundle(year, timeout=args.timeout, local_repo_root=local_repo_root)
            teams = build_team_payloads(bundle)
            matches = build_match_payloads(bundle)
            standings = build_standing_payloads(bundle)
            print(
                f"  {year} ({HOST_COUNTRIES.get(year, '?')}): "
                f"{len(teams)} đội, {len(matches)} trận, {len(standings)} dòng BXH "
                f"[nguồn BXH: {standings[0]['source'] if standings else 'n/a'}]"
            )
        print("[openfootball-sync] Dry-run xong, không có gì được ghi vào DB.")
        return 0

    # Import muộn để DATABASE_URL override có hiệu lực trước khi engine được tạo.
    # Phải import app.database.base TRƯỚC để toàn bộ model được đăng ký với
    # SQLAlchemy registry - nếu không, các relationship() dùng tên chuỗi sẽ
    # báo lỗi "failed to locate a name".
    from app.database.base import Base  # noqa: F401
    from app.database.session import SessionLocal

    stats = {
        "world_cups_created": 0,
        "world_cups_updated": 0,
        "teams_created": 0,
        "matches_created": 0,
        "matches_updated": 0,
        "matches_skipped_unknown_team": 0,
        "standings_created": 0,
        "standings_updated": 0,
    }

    db = SessionLocal()
    try:
        for year in years:
            print(f"[openfootball-sync] Đang xử lý năm {year}...")
            bundle = fetch_year_bundle(year, timeout=args.timeout, local_repo_root=local_repo_root)
            sync_year(db, bundle, stats=stats)
            db.commit()
        print("[openfootball-sync] Hoàn tất.")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
