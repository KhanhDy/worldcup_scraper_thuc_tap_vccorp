import unittest

from app.crawler.sources.vn_news_source import (
    NEWS_SOURCES,
    detect_world_cup_year,
    extract_article_links,
    is_world_cup_relevant,
    parse_article,
)

VNEXPRESS_LISTING_HTML = """
<html><body>
<div class="item-news">
  <h2><a href="https://vnexpress.net/fifa-bao-ve-quyet-dinh-var-5103055.html">FIFA bảo vệ quyết định VAR</a></h2>
</div>
<div class="item-news">
  <h2><a href="https://vnexpress.net/cucurella-xam-hinh-5102910.html">Cucurella xăm hình</a></h2>
</div>
<a href="https://vnexpress.net/the-thao">Chuyên mục (không phải bài viết)</a>
<a href="https://vnexpress.net/fifa-bao-ve-quyet-dinh-var-5103055.html#box_comment_vne">link trùng có #anchor</a>
</body></html>
"""

VNEXPRESS_ARTICLE_HTML = """
<html><head>
<meta property="og:title" content="FIFA bảo vệ quyết định VAR ở trận Argentina thắng Thụy Sĩ - Báo VnExpress" />
<meta property="og:description" content="FIFA khẳng định quyết định VAR trong trận Argentina gặp Thụy Sĩ tại tứ kết World Cup 2026 hoàn toàn phù hợp." />
<meta property="og:image" content="https://vcdn1-thethao.vnecdn.net/2026/07/29/embolo.jpg" />
<meta name="pubdate" content="2026-07-29T20:15:00+07:00" />
<meta name="keywords" content="World Cup 2026, FIFA, VAR, Argentina" />
</head>
<body>
<nav><a href="/">Trang chủ</a><a href="/the-thao">Thể thao</a></nav>
<article class="fck_detail">
<h1>FIFA bảo vệ quyết định VAR ở trận Argentina thắng Thụy Sĩ</h1>
<p class="Normal">Trái ngược quan điểm từ IFAB, FIFA khẳng định quyết định VAR trong trận Argentina gặp Thụy Sĩ tại tứ kết World Cup 2026 hoàn toàn phù hợp với luật.</p>
<p class="Normal">Đây là pha bóng gây tranh cãi lớn nhất kể từ đầu giải, khi trọng tài rút thẻ đỏ sau khi tham khảo VAR ở phút 89 của trận đấu then chốt.</p>
<p class="Normal">Nhiều chuyên gia bóng đá châu Âu tiếp tục lên tiếng phản đối quyết định này trong những ngày sau đó.</p>
</article>
<footer><p>Bản quyền VnExpress. Liên hệ quảng cáo tại đây với đội ngũ chăm sóc khách hàng của chúng tôi.</p></footer>
</body></html>
"""

TUOITRE_ARTICLE_HTML = """
<html><head>
<meta property="og:title" content="UEFA triệu tập 55 liên đoàn để 'quyết tâm chống lại FIFA'" />
<meta property="og:description" content="Chiều 30-7, UEFA họp với 55 liên đoàn thành viên để phản ứng kế hoạch của FIFA." />
<meta property="article:published_time" content="2026-07-30T14:21:00+07:00" />
<meta name="news_keywords" content="Messi, world cup, fifa, UEFA, Ronaldo" />
</head>
<body>
<div id="menu-wrap"><a href="/the-thao.htm">Thể thao</a></div>
<div id="content-detail">
<h1>UEFA triệu tập 55 liên đoàn để 'quyết tâm chống lại FIFA'</h1>
<p>Chiều ngày 30-7 (giờ châu Âu) sẽ diễn ra cuộc họp quan trọng của UEFA với 55 Liên đoàn thành viên, nhằm thống nhất phản ứng kế hoạch gây tranh cãi về World Cup của FIFA sau khi World Cup 2026 khép lại.</p>
<p>Khả năng các đội tuyển châu Âu tẩy chay một số giải đấu của FIFA cũng được đưa ra thảo luận trong cuộc họp lần này.</p>
</div>
<div class="box-comment"><p>Hãy là người đầu tiên bình luận về bài viết này để lại ý kiến của bạn nhé bạn đọc.</p></div>
</body></html>
"""


class ExtractArticleLinksTests(unittest.TestCase):
    def test_extracts_only_article_urls_and_dedupes_anchor(self) -> None:
        links = extract_article_links(VNEXPRESS_LISTING_HTML, NEWS_SOURCES["vnexpress"])
        self.assertEqual(
            links,
            [
                "https://vnexpress.net/fifa-bao-ve-quyet-dinh-var-5103055.html",
                "https://vnexpress.net/cucurella-xam-hinh-5102910.html",
            ],
        )


class ParseArticleTests(unittest.TestCase):
    def test_vnexpress_article(self) -> None:
        result = parse_article(
            VNEXPRESS_ARTICLE_HTML,
            "https://vnexpress.net/fifa-bao-ve-quyet-dinh-var-5103055.html",
            NEWS_SOURCES["vnexpress"],
        )
        self.assertIn("FIFA bảo vệ quyết định VAR", result["title"])
        self.assertEqual(result["source"], "VnExpress")
        self.assertIn("World Cup 2026", result["keywords"])
        self.assertEqual(result["world_cup_year"], 2026)
        self.assertIsNotNone(result["published_at"])
        self.assertEqual(result["published_at"].year, 2026)
        # Nội dung lấy từ khối <article>, không lẫn text trong <footer>
        self.assertIn("trọng tài rút thẻ đỏ", result["content"])
        self.assertNotIn("Liên hệ quảng cáo", result["content"])

    def test_tuoitre_article_uses_published_time_meta(self) -> None:
        result = parse_article(
            TUOITRE_ARTICLE_HTML,
            "https://tuoitre.vn/uefa-trieu-tap-55-lien-doan-100260730124834908.htm",
            NEWS_SOURCES["tuoitre"],
        )
        self.assertEqual(result["published_at"].hour, 14)
        self.assertIn("tẩy chay một số giải đấu", result["content"])
        # Box bình luận phải bị loại khỏi content vì nằm trong class chứa "comment"
        self.assertNotIn("Hãy là người đầu tiên bình luận", result["content"])
        self.assertEqual(result["world_cup_year"], 2026)


class DetectWorldCupYearTests(unittest.TestCase):
    def test_picks_most_mentioned_year(self) -> None:
        text = "World Cup 2018 rất khác World Cup 2022. Nhưng World Cup 2022 mới là gần nhất."
        self.assertEqual(detect_world_cup_year(text), 2022)

    def test_falls_back_to_default_when_no_year_found(self) -> None:
        self.assertEqual(detect_world_cup_year("Không nhắc năm nào cả", default_year=2026), 2026)


THANHNIEN_LISTING_RELATIVE_HREF_HTML = """
<html><body>
<h3><a href="/xac-dinh-tran-dau-dau-tien-tro-lai-cua-messi-sau-chung-ket-world-cup-2026-185260730090821063.htm">Xác định trận đấu đầu tiên trở lại của Messi</a></h3>
<h3><a href="/fifa-se-ky-luat-cau-thu-argentina-va-tay-ban-nha-vi-au-da-paredes-nang-nhat-185260730002358563.htm">FIFA sẽ kỷ luật cầu thủ</a></h3>
<a href="/the-thao.htm">Thể thao (không phải bài viết)</a>
</body></html>
"""


class ExtractArticleLinksRelativeHrefTests(unittest.TestCase):
    def test_resolves_relative_href_against_base_url(self) -> None:
        links = extract_article_links(
            THANHNIEN_LISTING_RELATIVE_HREF_HTML,
            NEWS_SOURCES["thanhnien"],
            base_url="https://thanhnien.vn/the-thao/world-cup-2026.htm",
        )
        self.assertEqual(
            links,
            [
                "https://thanhnien.vn/xac-dinh-tran-dau-dau-tien-tro-lai-cua-messi-sau-chung-ket-world-cup-2026-185260730090821063.htm",
                "https://thanhnien.vn/fifa-se-ky-luat-cau-thu-argentina-va-tay-ban-nha-vi-au-da-paredes-nang-nhat-185260730002358563.htm",
            ],
        )

    def test_without_base_url_relative_href_is_ignored(self) -> None:
        links = extract_article_links(THANHNIEN_LISTING_RELATIVE_HREF_HTML, NEWS_SOURCES["thanhnien"])
        self.assertEqual(links, [])


TUOITRE_ARTICLE_WITH_BOILERPLATE_HTML = """
<html><head>
<meta property="og:title" content="Messi lỡ hẹn buổi tập cuối trước bán kết World Cup 2026" />
<meta property="og:description" content="Messi vắng mặt buổi tập cuối cùng trước trận bán kết World Cup 2026 vì lý do cá nhân." />
<meta property="article:published_time" content="2026-07-28T09:00:00+07:00" />
</head>
<body>
<div id="content-detail">
<h1>Messi lỡ hẹn buổi tập cuối trước bán kết World Cup 2026</h1>
<p>Messi đã không xuất hiện trong buổi tập cuối cùng của đội tuyển Argentina trước trận bán kết World Cup 2026 diễn ra vào cuối tuần này.</p>
<p>HLV Scaloni cho biết đây chỉ là biện pháp phòng ngừa để giữ sức cho ngôi sao 39 tuổi trước trận đấu quan trọng.</p>
<p>Thêm chuyên mục, tăng trải nghiệm với Tuổi Trẻ Sao</p>
<p>Từ ngày 1-1-2023, Tuổi Trẻ Online giới thiệu Tuổi Trẻ Sao - phiên bản đặc biệt dành riêng cho các thành viên với nhiều chuyên mục và trải nghiệm thú vị, bao gồm nhiều nội dung phong phú khác nhau dành cho độc giả thân thiết của báo.</p>
<p>Báo Tuổi Trẻ phát triển Tuổi Trẻ Sao nhằm từng bước nâng cao chất lượng nội dung phục vụ độc giả trung thành của mình trong suốt nhiều năm qua.</p>
</div>
</body></html>
"""


class ExtractContentBoilerplateTests(unittest.TestCase):
    def test_tuoitre_sao_promo_block_is_excluded_even_in_same_parent(self) -> None:
        result = parse_article(
            TUOITRE_ARTICLE_WITH_BOILERPLATE_HTML,
            "https://tuoitre.vn/messi-lo-hen-buoi-tap-100260728090000001.htm",
            NEWS_SOURCES["tuoitre"],
        )
        self.assertIn("giữ sức cho ngôi sao", result["content"])
        self.assertNotIn("Tuổi Trẻ Sao", result["content"])
        self.assertNotIn("1-1-2023", result["content"])


class IsWorldCupRelevantTests(unittest.TestCase):
    def test_relevant_article_passes(self) -> None:
        self.assertTrue(is_world_cup_relevant("Messi tại World Cup 2026", "", ""))

    def test_unrelated_stock_news_is_rejected(self) -> None:
        self.assertFalse(
            is_world_cup_relevant(
                "VN-Index lao dốc xuống dưới 1.700 điểm",
                "Hàng loạt cổ phiếu giảm mạnh và rớt sàn như PNJ, MWG",
                "",
            )
        )

    def test_unrelated_football_news_without_world_cup_mention_is_rejected(self) -> None:
        self.assertFalse(is_world_cup_relevant("Real Madrid thắng đậm ở Champions League", "", ""))


if __name__ == "__main__":
    unittest.main()
