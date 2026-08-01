"""
Nguồn dữ liệu: openfootball/worldcup.json (GitHub, public domain, no API key)
https://github.com/openfootball/worldcup.json

Module này chỉ chịu trách nhiệm FETCH + PARSE dữ liệu thô thành các dict
đơn giản, KHÔNG đụng tới DB/ORM ở đây để dễ unit test độc lập.
Việc ghi vào database nằm ở app/crawler/sync_openfootball.py.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests

BASE_RAW_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master"

# Các kỳ World Cup nam đã/sẽ diễn ra (1942, 1946 không tổ chức do Thế chiến II)
WORLD_CUP_YEARS: list[int] = [
    1930, 1934, 1938, 1950, 1954, 1958, 1962, 1966, 1970, 1974, 1978,
    1982, 1986, 1990, 1994, 1998, 2002, 2006, 2010, 2014, 2018, 2022, 2026,
]

# Nước chủ nhà từng kỳ - dữ liệu lịch sử cố định, không có trong bộ
# openfootball nên khai báo tĩnh ở đây (không đổi theo thời gian).
HOST_COUNTRIES: dict[int, str] = {
    1930: "Uruguay",
    1934: "Italy",
    1938: "France",
    1950: "Brazil",
    1954: "Switzerland",
    1958: "Sweden",
    1962: "Chile",
    1966: "England",
    1970: "Mexico",
    1974: "West Germany",
    1978: "Argentina",
    1982: "Spain",
    1986: "Mexico",
    1990: "Italy",
    1994: "United States",
    1998: "France",
    2002: "South Korea / Japan",
    2006: "Germany",
    2010: "South Africa",
    2014: "Brazil",
    2018: "Russia",
    2022: "Qatar",
    2026: "Canada / Mexico / United States",
}


class OpenFootballFetchError(RuntimeError):
    pass


# Các cặp tên bị lệch ĐÃ XÁC MINH giữa worldcup.teams.json/standings.json và
# worldcup.json (match list) trong cùng một năm nguồn openfootball (không
# phải suy đoán - phát hiện khi đối chiếu dữ liệu thật). Nếu sau này gặp
# thêm năm/đội nào bị lệch tương tự, thêm vào đây.
KNOWN_NAME_ALIASES: dict[str, str] = {
    "USA": "United States",  # 2014: teams.json="United States", matches="USA"
}


def _canonical_team_name(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    return KNOWN_NAME_ALIASES.get(name, name)


@dataclass
class YearBundle:
    """Toàn bộ dữ liệu thô (đã parse JSON) của một kỳ World Cup."""

    year: int
    matches_payload: dict[str, Any]
    teams_payload: Optional[dict[str, Any]] = None
    standings_payload: Optional[dict[str, Any]] = None

    @property
    def matches(self) -> list[dict[str, Any]]:
        return list(self.matches_payload.get("matches") or [])


# ---------------------------------------------------------------------------
# Fetch (HTTP hoặc đọc từ thư mục local đã git clone sẵn)
# ---------------------------------------------------------------------------

def _fetch_json_http(url: str, timeout: int = 30) -> Optional[dict[str, Any]]:
    response = requests.get(url, timeout=timeout)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def _fetch_json_local(root: Path, relative_path: str) -> Optional[dict[str, Any]]:
    file_path = root / relative_path
    if not file_path.exists():
        return None
    return json.loads(file_path.read_text(encoding="utf-8"))


def fetch_year_bundle(
    year: int,
    timeout: int = 30,
    local_repo_root: Optional[Path] = None,
) -> YearBundle:
    """
    Lấy dữ liệu thô cho một năm.

    - Nếu local_repo_root được cung cấp: đọc từ thư mục đã `git clone` sẵn
      repo openfootball/worldcup.json (nhanh hơn, không phụ thuộc mạng khi
      chạy lại nhiều lần).
    - Ngược lại: gọi HTTP tới raw.githubusercontent.com.
    """
    matches_rel = f"{year}/worldcup.json"
    teams_rel = f"{year}/worldcup.teams.json"
    standings_rel = f"{year}/worldcup.standings.json"

    if local_repo_root is not None:
        matches_payload = _fetch_json_local(local_repo_root, matches_rel)
        if matches_payload is None:
            raise OpenFootballFetchError(f"Không tìm thấy {matches_rel} trong {local_repo_root}")
        teams_payload = _fetch_json_local(local_repo_root, teams_rel)
        standings_payload = _fetch_json_local(local_repo_root, standings_rel)
    else:
        matches_payload = _fetch_json_http(f"{BASE_RAW_URL}/{matches_rel}", timeout)
        if matches_payload is None:
            raise OpenFootballFetchError(f"Không tìm thấy {matches_rel} trên GitHub")
        teams_payload = _fetch_json_http(f"{BASE_RAW_URL}/{teams_rel}", timeout)
        standings_payload = _fetch_json_http(f"{BASE_RAW_URL}/{standings_rel}", timeout)

    return YearBundle(
        year=year,
        matches_payload=matches_payload,
        teams_payload=teams_payload,
        standings_payload=standings_payload,
    )


# ---------------------------------------------------------------------------
# Parse các trường "khó" trong dữ liệu thô
# ---------------------------------------------------------------------------

def parse_ground(ground: Optional[str]) -> tuple[str, str]:
    """
    'Luzhniki Stadium, Moscow' -> ('Luzhniki Stadium', 'Moscow')
    'Atlanta' (WC2026, không có dấu phẩy) -> ('Atlanta', 'Atlanta')
    None/'' -> ('Unknown', 'Unknown')
    """
    if not ground:
        return "Unknown", "Unknown"
    ground = ground.strip()
    if "," in ground:
        stadium, city = ground.rsplit(",", 1)
        return stadium.strip(), city.strip()
    return ground, ground


def parse_minute(raw: Any) -> tuple[int, Optional[int]]:
    """
    12          -> (12, None)
    '90+6'      -> (90, 6)
    {'minute': 45, 'offset': 1} đã tách sẵn ở build_goal_payloads, hàm này
    chỉ xử lý giá trị số/chuỗi thô.
    """
    if raw is None:
        return 0, None
    text = str(raw)
    match = re.match(r"^(\d+)(?:\+(\d+))?$", text.strip())
    if not match:
        return 0, None
    minute = int(match.group(1))
    extra = int(match.group(2)) if match.group(2) else None
    return minute, extra


def parse_match_score(score: dict[str, Any]) -> dict[str, Any]:
    """
    Trả về điểm số cuối cùng (ưu tiên hiệp phụ nếu có) + điểm luân lưu.
    score có thể chứa các key: ht (hiệp 1), ft (90p), et (hiệp phụ), p (luân lưu)
    """
    ft = score.get("ft")
    et = score.get("et")
    pens = score.get("p")

    final = et if et is not None else ft
    if final is None:
        final = [None, None]

    team_1_score, team_2_score = final[0], final[1]
    team_1_pen, team_2_pen = (pens[0], pens[1]) if pens is not None else (None, None)

    winner: Optional[str]
    if pens is not None:
        winner = "team1" if pens[0] > pens[1] else "team2"
    elif team_1_score is not None and team_2_score is not None and team_1_score != team_2_score:
        winner = "team1" if team_1_score > team_2_score else "team2"
    else:
        winner = None

    return {
        "team_1_score": team_1_score,
        "team_2_score": team_2_score,
        "team_1_penalty_score": team_1_pen,
        "team_2_penalty_score": team_2_pen,
        "winner": winner,
    }


def parse_match_date(date_str: Optional[str]) -> datetime:
    if not date_str:
        return datetime(1900, 1, 1)
    return datetime.strptime(date_str.strip(), "%Y-%m-%d")


# ---------------------------------------------------------------------------
# Xây dựng payload cấp cao từ YearBundle
# ---------------------------------------------------------------------------

def build_world_cup_payload(year: int) -> dict[str, Any]:
    return {
        "year": year,
        "host_country": HOST_COUNTRIES.get(year, "Unknown"),
    }


def build_team_payloads(bundle: YearBundle) -> list[dict[str, Any]]:
    """
    Ưu tiên dùng worldcup.teams.json (có từ 2014, KHÔNG có ở 2022) vì có
    code + continent. Nếu không có (2022 và các năm trước 2014), suy ra
    danh sách đội từ chính các trận đấu.

    Lưu ý format file này KHÔNG đồng nhất giữa các năm:
      - 2014/2018: {"name": ..., "teams": [{"name","code","continent","confed"}]}
      - 2026:      [{"name","fifa_code","continent","confed", ...}]  (list trần)

    Nguồn dữ liệu cũng có lúc TỰ MÂU THUẪN trong cùng một năm: VD năm 2014,
    worldcup.teams.json ghi "United States" nhưng worldcup.json (các trận)
    lại dùng "USA" cho chính đội đó. Nếu chỉ dựa vào teams.json, các trận
    của đội bị lệch tên sẽ không map được team_id và bị bỏ qua. Vì vậy luôn
    đối chiếu thêm với tên đội xuất hiện trong match list và bổ sung phần
    thiếu (không có code/continent cho phần bổ sung này).
    """
    teams: list[dict[str, Any]] = []
    seen: set[str] = set()

    if bundle.teams_payload:
        raw_list = (
            bundle.teams_payload
            if isinstance(bundle.teams_payload, list)
            else bundle.teams_payload.get("teams", [])
        )
        for team in raw_list:
            name = _canonical_team_name(team.get("name"))
            if not name or name in seen:
                continue
            seen.add(name)
            teams.append(
                {
                    "name": name,
                    "fifa_code": team.get("code") or team.get("fifa_code"),
                    "continent": team.get("continent"),
                }
            )

    # Bổ sung mọi tên đội xuất hiện trong trận đấu mà chưa có trong danh sách
    # trên (dù là do teams.json thiếu, hay do lệch tên như ví dụ USA/2014).
    for match in bundle.matches:
        for key in ("team1", "team2"):
            name = _canonical_team_name(match.get(key))
            if name and name not in seen:
                seen.add(name)
                teams.append({"name": name, "fifa_code": None, "continent": None})

    return teams


def build_match_payloads(bundle: YearBundle) -> list[dict[str, Any]]:
    """
    Trả về list dict "trung gian" (chưa có team_id thật, vẫn dùng tên đội)
    để sync_openfootball.py map sang id sau khi upsert Team.
    """
    records = []
    for match in bundle.matches:
        stadium, city = parse_ground(match.get("ground"))
        score = parse_match_score(match.get("score") or {})
        records.append(
            {
                "team_1_name": _canonical_team_name(match.get("team1")),
                "team_2_name": _canonical_team_name(match.get("team2")),
                "stage": (match.get("round") or "Unknown")[:50],
                "group_name": match.get("group"),
                "match_date": parse_match_date(match.get("date")),
                "stadium": stadium[:100],
                "city": city[:100],
                "team_1_score": score["team_1_score"] or 0,
                "team_2_score": score["team_2_score"] or 0,
                "team_1_penalty_score": score["team_1_penalty_score"],
                "team_2_penalty_score": score["team_2_penalty_score"],
                "winner": score["winner"],  # "team1" | "team2" | None -> resolve id sau
            }
        )
    return records


# Duy nhất World Cup 1950 quyết định chức vô địch bằng một "vòng chung kết"
# đấu vòng tròn tính điểm (4 đội) thay vì một trận Chung kết duy nhất -
# ĐÃ XÁC MINH đây là năm duy nhất trong toàn bộ 23 kỳ có kiểu vòng round-robin
# mà nguồn dữ liệu không gắn field "group" (nên bị _standard_group_standings
# bỏ sót nếu không xử lý riêng).
ROUND_ROBIN_STAGES_WITHOUT_GROUP_FIELD = {"Final Round"}


def _standard_group_standings(bundle: YearBundle) -> list[dict[str, Any]]:
    """Tự tính BXH bảng từ kết quả trận vòng bảng (dùng cho năm không có
    sẵn worldcup.standings.json, tức trước 2014)."""
    grouped: dict[str, dict[str, dict[str, Any]]] = {}

    for match in bundle.matches:
        group_name = match.get("group")
        if not group_name and match.get("round") in ROUND_ROBIN_STAGES_WITHOUT_GROUP_FIELD:
            group_name = match["round"]
        if not group_name:
            continue
        score = match.get("score") or {}
        # BXH vòng bảng chỉ tính theo tỉ số 90 phút (không hiệp phụ/luân lưu)
        ft = score.get("ft")
        if ft is None:
            continue
        team_1_name, team_2_name = _canonical_team_name(match.get("team1")), _canonical_team_name(match.get("team2"))
        if not team_1_name or not team_2_name:
            continue

        grouped.setdefault(group_name, {})
        for name in (team_1_name, team_2_name):
            grouped[group_name].setdefault(
                name,
                {"played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0},
            )

        a, b = grouped[group_name][team_1_name], grouped[group_name][team_2_name]
        s1, s2 = ft[0], ft[1]
        a["played"] += 1
        b["played"] += 1
        a["goals_for"] += s1
        a["goals_against"] += s2
        b["goals_for"] += s2
        b["goals_against"] += s1
        if s1 > s2:
            a["wins"] += 1
            b["losses"] += 1
            a["points"] += 3
        elif s2 > s1:
            b["wins"] += 1
            a["losses"] += 1
            b["points"] += 3
        else:
            a["draws"] += 1
            b["draws"] += 1
            a["points"] += 1
            b["points"] += 1

    rows = []
    for group_name, teams in grouped.items():
        ordered = sorted(
            teams.items(),
            key=lambda item: (
                -item[1]["points"],
                -(item[1]["goals_for"] - item[1]["goals_against"]),
                -item[1]["goals_for"],
                item[0],
            ),
        )
        for rank, (team_name, stats) in enumerate(ordered, start=1):
            rows.append(
                {
                    "team_name": team_name,
                    "group_name": group_name,
                    "rank": rank,
                    "played": stats["played"],
                    "wins": stats["wins"],
                    "draws": stats["draws"],
                    "losses": stats["losses"],
                    "goals_for": stats["goals_for"],
                    "goals_against": stats["goals_against"],
                    "goal_difference": stats["goals_for"] - stats["goals_against"],
                    "points": stats["points"],
                    # heuristic: 2 đội đầu bảng đi tiếp - đúng với đa số các kỳ
                    # có bảng 4 đội; với thể thức khác (VD 1950, 1974, 1978
                    # dùng vòng bảng thứ hai) cần tự kiểm tra lại thủ công.
                    "qualified": rank <= 2,
                    "source": "computed",
                }
            )
    return rows


def build_standing_payloads(bundle: YearBundle) -> list[dict[str, Any]]:
    """
    Ưu tiên worldcup.standings.json (2014, 2018, 2022 - dữ liệu chính thức).
    Nếu không có, tự tính từ kết quả trận đấu vòng bảng.
    """
    if bundle.standings_payload:
        rows = []
        for group in bundle.standings_payload.get("groups", []):
            group_name = group.get("name")
            for entry in group.get("standings", []):
                goals_for = entry.get("goals_for", 0)
                goals_against = entry.get("goals_against", 0)
                rows.append(
                    {
                        "team_name": _canonical_team_name(entry["team"]["name"]),
                        "group_name": group_name,
                        "rank": entry.get("pos"),
                        "played": entry.get("played", 0),
                        "wins": entry.get("won", 0),
                        "draws": entry.get("drawn", 0),
                        "losses": entry.get("lost", 0),
                        "goals_for": goals_for,
                        "goals_against": goals_against,
                        "goal_difference": goals_for - goals_against,
                        "points": entry.get("pts", 0),
                        "qualified": entry.get("pos", 99) <= 2,
                        "source": "official",
                    }
                )
        return rows

    return _standard_group_standings(bundle)
