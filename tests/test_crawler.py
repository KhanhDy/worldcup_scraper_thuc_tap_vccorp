import pathlib
import unittest

from app.crawler.cli import build_match_record, build_team_map, extract_match_entries, extract_next_data


class CrawlerParsingTests(unittest.TestCase):
    def setUp(self) -> None:
        html = pathlib.Path(__file__).resolve().parents[1] / "fifa_matches_page.html"
        self.html = html.read_text(encoding="utf-8", errors="ignore")
        self.next_data = extract_next_data(self.html)
        self.matches = extract_match_entries(self.next_data)

    def test_extract_match_entries_finds_fixture_matches(self) -> None:
        self.assertGreater(len(self.matches), 0)
        self.assertIn("idMatch", self.matches[0])

    def test_build_team_map_contains_known_teams(self) -> None:
        team_map = build_team_map(self.matches)
        self.assertIn("43922", team_map)
        self.assertEqual(team_map["43922"]["name"], "Argentina")

    def test_build_match_record_uses_fixture_fields(self) -> None:
        record = build_match_record(self.matches[0], 2026)
        self.assertEqual(record["world_cup_id"], 2026)
        self.assertEqual(record["stage"], "Round of 16")
        self.assertEqual(record["team_1_score"], 0)


if __name__ == "__main__":
    unittest.main()
