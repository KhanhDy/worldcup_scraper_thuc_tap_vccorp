import pathlib
import unittest

from app.crawler.sources.openfootball_source import (
    build_match_payloads,
    build_standing_payloads,
    build_team_payloads,
    build_world_cup_payload,
    fetch_year_bundle,
    parse_ground,
    parse_match_score,
    parse_minute,
)

FIXTURES_ROOT = pathlib.Path(__file__).resolve().parent / "fixtures" / "openfootball"


class ParsingHelpersTests(unittest.TestCase):
    def test_parse_ground_with_comma(self) -> None:
        stadium, city = parse_ground("Luzhniki Stadium, Moscow")
        self.assertEqual(stadium, "Luzhniki Stadium")
        self.assertEqual(city, "Moscow")

    def test_parse_ground_without_comma(self) -> None:
        stadium, city = parse_ground("Atlanta")
        self.assertEqual(stadium, "Atlanta")
        self.assertEqual(city, "Atlanta")

    def test_parse_ground_empty(self) -> None:
        self.assertEqual(parse_ground(None), ("Unknown", "Unknown"))

    def test_parse_minute_plain(self) -> None:
        self.assertEqual(parse_minute(12), (12, None))

    def test_parse_minute_with_offset(self) -> None:
        self.assertEqual(parse_minute("90+6"), (90, 6))

    def test_parse_match_score_regular_time(self) -> None:
        result = parse_match_score({"ht": [1, 1], "ft": [1, 1]})
        self.assertEqual(result["team_1_score"], 1)
        self.assertIsNone(result["winner"])

    def test_parse_match_score_penalty_decides_winner(self) -> None:
        result = parse_match_score({"ht": [1, 1], "ft": [1, 1], "et": [1, 1], "p": [3, 4]})
        self.assertEqual(result["winner"], "team2")
        self.assertEqual(result["team_1_score"], 1)
        self.assertEqual(result["team_1_penalty_score"], 3)
        self.assertEqual(result["team_2_penalty_score"], 4)

    def test_parse_match_score_extra_time_decides_winner(self) -> None:
        result = parse_match_score({"ht": [0, 1], "ft": [1, 1], "et": [2, 1]})
        self.assertEqual(result["winner"], "team1")
        self.assertEqual(result["team_1_score"], 2)


class YearBundle2018Tests(unittest.TestCase):
    """2018 có đủ worldcup.json + teams.json + standings.json (dữ liệu chính thức)."""

    def setUp(self) -> None:
        self.bundle = fetch_year_bundle(2018, local_repo_root=FIXTURES_ROOT)

    def test_matches_loaded(self) -> None:
        self.assertEqual(len(self.bundle.matches), 64)

    def test_world_cup_payload(self) -> None:
        payload = build_world_cup_payload(2018)
        self.assertEqual(payload, {"year": 2018, "host_country": "Russia"})

    def test_team_payloads_use_official_teams_file(self) -> None:
        teams = build_team_payloads(self.bundle)
        self.assertEqual(len(teams), 32)
        croatia = next(t for t in teams if t["name"] == "Croatia")
        self.assertEqual(croatia["fifa_code"], "CRO")
        self.assertEqual(croatia["continent"], "Europe")

    def test_match_payload_penalty_shootout(self) -> None:
        matches = build_match_payloads(self.bundle)
        spain_russia = next(
            m for m in matches if {m["team_1_name"], m["team_2_name"]} == {"Spain", "Russia"}
        )
        self.assertEqual(spain_russia["team_1_score"], 1)
        self.assertEqual(spain_russia["team_2_score"], 1)
        self.assertEqual(spain_russia["team_1_penalty_score"], 3)
        self.assertEqual(spain_russia["team_2_penalty_score"], 4)
        self.assertEqual(spain_russia["winner"], "team2")
        self.assertEqual(spain_russia["stadium"], "Luzhniki Stadium")
        self.assertEqual(spain_russia["city"], "Moscow")

    def test_standing_payload_uses_official_file(self) -> None:
        standings = build_standing_payloads(self.bundle)
        uruguay = next(s for s in standings if s["team_name"] == "Uruguay")
        self.assertEqual(uruguay["rank"], 1)
        self.assertEqual(uruguay["points"], 9)
        self.assertTrue(uruguay["qualified"])
        self.assertEqual(uruguay["source"], "official")


class YearBundle1966Tests(unittest.TestCase):
    """1966 KHÔNG có teams.json/standings.json -> phải tự suy luận."""

    def setUp(self) -> None:
        self.bundle = fetch_year_bundle(1966, local_repo_root=FIXTURES_ROOT)

    def test_teams_derived_from_matches(self) -> None:
        teams = build_team_payloads(self.bundle)
        self.assertIn("England", [t["name"] for t in teams])
        self.assertIsNone(teams[0]["fifa_code"])

    def test_standings_are_computed(self) -> None:
        standings = build_standing_payloads(self.bundle)
        self.assertTrue(standings)
        self.assertEqual(standings[0]["source"], "computed")


class YearBundle1950Tests(unittest.TestCase):
    """1950: chức vô địch quyết định bằng vòng tròn tính điểm 4 đội
    ("Final Round"), không có trận nào tên "Final", và match không có
    field "group" cho vòng này -> phải tự nhận diện đặc biệt."""

    def setUp(self) -> None:
        self.bundle = fetch_year_bundle(1950, local_repo_root=FIXTURES_ROOT)

    def test_final_round_produces_standing_rows(self) -> None:
        standings = build_standing_payloads(self.bundle)
        final_round_rows = [s for s in standings if s["group_name"] == "Final Round"]
        self.assertEqual(len(final_round_rows), 4)
        uruguay = next(s for s in final_round_rows if s["team_name"] == "Uruguay")
        brazil = next(s for s in final_round_rows if s["team_name"] == "Brazil")
        self.assertEqual(uruguay["rank"], 1)
        self.assertEqual(brazil["rank"], 2)


if __name__ == "__main__":
    unittest.main()
