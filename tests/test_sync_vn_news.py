import os
import unittest
from unittest import mock

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.crawler.sources.vn_news_source import NEWS_SOURCES  # noqa: E402
from app.crawler import sync_vn_news  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.session import engine, SessionLocal  # noqa: E402
from app.models.world_cup import WorldCup  # noqa: E402
from app.models.news import News  # noqa: E402

VNEXPRESS_ARTICLE_HTML = """
<html><head>
<meta property="og:title" content="FIFA bảo vệ quyết định VAR ở trận Argentina thắng Thụy Sĩ" />
<meta property="og:description" content="FIFA khẳng định quyết định VAR trong trận Argentina gặp Thụy Sĩ tại tứ kết World Cup 2026 hoàn toàn phù hợp." />
<meta property="og:image" content="https://vcdn1-thethao.vnecdn.net/2026/07/29/embolo.jpg" />
<meta name="pubdate" content="2026-07-29T20:15:00+07:00" />
<meta name="keywords" content="World Cup 2026, FIFA, VAR" />
</head>
<body>
<article class="fck_detail">
<h1>FIFA bảo vệ quyết định VAR ở trận Argentina thắng Thụy Sĩ</h1>
<p class="Normal">Trái ngược quan điểm từ IFAB, FIFA khẳng định quyết định VAR trong trận Argentina gặp Thụy Sĩ tại tứ kết World Cup 2026 hoàn toàn phù hợp với luật.</p>
<p class="Normal">Đây là pha bóng gây tranh cãi lớn nhất kể từ đầu giải, khi trọng tài rút thẻ đỏ sau khi tham khảo VAR.</p>
</article>
</body></html>
"""


class SyncVnNewsIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.create_all(engine)
        self.db = SessionLocal()
        self.db.add(WorldCup(year=2026, host_country="Canada / Mexico / United States"))
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(engine)

    def test_sync_source_creates_news_row_with_correct_world_cup(self) -> None:
        fake_url = "https://vnexpress.net/fifa-bao-ve-quyet-dinh-var-5103055.html"
        with mock.patch.object(sync_vn_news, "discover_article_urls", return_value=[fake_url]), \
             mock.patch.object(sync_vn_news, "fetch_html", return_value=VNEXPRESS_ARTICLE_HTML):
            stats = {
                "created": 0, "skipped_existing": 0, "skipped_empty": 0, "skipped_not_world_cup": 0,
                "skipped_unknown_world_cup": 0, "fetch_errors": 0,
            }
            sync_vn_news.sync_source(
                self.db, "vnexpress", pages=1, limit=0, delay=0, default_wc_year=2026, stats=stats
            )
            self.db.commit()

        self.assertEqual(stats["created"], 1)
        row = self.db.query(News).filter(News.url == fake_url).first()
        self.assertIsNotNone(row)
        self.assertEqual(row.world_cup_id, 1)
        self.assertIn("FIFA bảo vệ quyết định VAR", row.title)
        self.assertEqual(row.published_at.year, 2026)

    def test_sync_source_dedupes_existing_url(self) -> None:
        fake_url = "https://vnexpress.net/fifa-bao-ve-quyet-dinh-var-5103055.html"
        with mock.patch.object(sync_vn_news, "discover_article_urls", return_value=[fake_url]), \
             mock.patch.object(sync_vn_news, "fetch_html", return_value=VNEXPRESS_ARTICLE_HTML):
            stats = {
                "created": 0, "skipped_existing": 0, "skipped_empty": 0, "skipped_not_world_cup": 0,
                "skipped_unknown_world_cup": 0, "fetch_errors": 0,
            }
            sync_vn_news.sync_source(self.db, "vnexpress", pages=1, limit=0, delay=0, default_wc_year=2026, stats=stats)
            self.db.commit()
            # chạy lại lần 2 với cùng URL
            sync_vn_news.sync_source(self.db, "vnexpress", pages=1, limit=0, delay=0, default_wc_year=2026, stats=stats)
            self.db.commit()

        self.assertEqual(stats["created"], 1)
        self.assertEqual(stats["skipped_existing"], 1)
        self.assertEqual(self.db.query(News).count(), 1)

    def test_sync_source_skips_when_world_cup_year_not_in_db(self) -> None:
        fake_url = "https://vnexpress.net/fifa-bao-ve-quyet-dinh-var-5103055.html"
        html_1998 = VNEXPRESS_ARTICLE_HTML.replace("2026", "1998")
        with mock.patch.object(sync_vn_news, "discover_article_urls", return_value=[fake_url]), \
             mock.patch.object(sync_vn_news, "fetch_html", return_value=html_1998):
            stats = {
                "created": 0, "skipped_existing": 0, "skipped_empty": 0, "skipped_not_world_cup": 0,
                "skipped_unknown_world_cup": 0, "fetch_errors": 0,
            }
            # default_wc_year cũng đặt 1998 để chắc chắn detect ra 1998, vốn KHÔNG có trong DB test (chỉ seed 2026)
            sync_vn_news.sync_source(self.db, "vnexpress", pages=1, limit=0, delay=0, default_wc_year=1998, stats=stats)
            self.db.commit()

        self.assertEqual(stats["created"], 0)
        self.assertEqual(stats["skipped_unknown_world_cup"], 1)


if __name__ == "__main__":
    unittest.main()
