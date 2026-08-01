"""
Crawler tin tức bóng đá / World Cup tiếng Việt: VnExpress, Tuổi Trẻ, Thanh Niên.

Thiết kế 2 tầng, tách biệt fetch/parse (module này) khỏi việc ghi DB
(app/crawler/sync_vn_news.py), theo đúng pattern đã dùng cho crawler
openfootball để dễ unit test độc lập.

LƯU Ý QUAN TRỌNG VỀ ĐỘ TIN CẬY:
Cấu trúc URL, danh sách bài (listing) và thẻ meta (og:*, article:published_time...)
được xác minh bằng cách fetch trực tiếp các trang thật của 3 báo tại thời điểm
viết crawler này. Tuy nhiên phần trích xuất NỘI DUNG bài viết (content) không
dựa vào tên class CSS cụ thể của từng báo (vì các trang này đổi giao diện khá
thường xuyên và không có cách xác minh class chắc chắn ổn định lâu dài) mà
dùng heuristic tổng quát: chọn khối chứa nhiều thẻ <p> "thật" (đủ dài, không
nằm trong nav/footer/quảng cáo) nhất trên trang. Heuristic này tương đối bền
với thay đổi giao diện nhưng không hoàn hảo 100% - nên chạy thử vài bài để
kiểm tra chất lượng content trước khi crawl số lượng lớn.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.crawler.sources.openfootball_source import WORLD_CUP_YEARS

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    # Tự động thử lại khi gặp lỗi mạng tạm thời (mất kết nối giữa chừng, 429,
    # 500-504) - đây là nguyên nhân phổ biến của lỗi "Response ended
    # prematurely" khi crawl số lượng lớn liên tục.
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_SESSION = _build_session()

# Các thẻ/khối chắc chắn không phải nội dung bài -> loại khỏi phần trích xuất content
NOISE_ANCESTOR_TAGS = {"nav", "footer", "header", "aside", "script", "style", "form"}
NOISE_CLASS_KEYWORDS = (
    "menu", "nav", "footer", "header", "share", "social", "comment", "box_comment",
    "quangcao", "advertisement", "related", "tin-lien-quan", "box-category",
    "breadcrumb", "sidebar", "widget", "subscribe", "author-info",
)

# Các đoạn quảng cáo/nội bộ toà soạn CỐ ĐỊNH, lặp lại y hệt trên nhiều bài của
# 1 báo, đôi khi nằm CHUNG thẻ cha với nội dung bài thật nên bộ lọc theo class
# (NOISE_CLASS_KEYWORDS) không chặn được. Lọc theo cụm từ nhận diện được.
BOILERPLATE_PARAGRAPH_MARKERS = (
    "tuổi trẻ sao",  # quảng cáo gói thành viên Tuổi Trẻ Online, lặp lại ở rất nhiều bài
    "tải app tuổi trẻ",
    "mời bạn đọc gửi bài",
    "vui lòng nhập bình luận",
)


@dataclass(frozen=True)
class NewsSource:
    key: str
    display_name: str
    listing_urls: tuple[str, ...]  # trang danh sách bài (đã xác minh tồn tại thật)
    article_url_pattern: re.Pattern
    paginate_template: Optional[str]  # None nếu site dùng infinite-scroll/JS (không paginate được bằng URL)
    max_pages: int


NEWS_SOURCES: dict[str, NewsSource] = {
    "vnexpress": NewsSource(
        key="vnexpress",
        display_name="VnExpress",
        listing_urls=(
            "https://vnexpress.net/the-thao/world-cup-2026/tin-tuc",
            "https://vnexpress.net/chu-de/world-cup-641",
        ),
        # vnexpress.net/<slug>-<7-8 chữ số>.html
        article_url_pattern=re.compile(r"^https://vnexpress\.net/[a-z0-9\-]+-\d{6,9}\.html$"),
        paginate_template="https://vnexpress.net/the-thao/world-cup-2026/tin-tuc-p{page}",
        max_pages=5,
    ),
    "tuoitre": NewsSource(
        key="tuoitre",
        display_name="Tuổi Trẻ",
        listing_urls=(
            "https://tuoitre.vn/world-cup.html",
            "https://tuoitre.vn/world-cup-2026.htm",
        ),
        # tuoitre.vn/<slug>-<id số>.htm
        article_url_pattern=re.compile(r"^https://tuoitre\.vn/[a-z0-9\-]+-\d{9,18}\.htm$"),
        # Tuổi Trẻ dùng nút "Xem thêm" tải bằng JS (AJAX) trên trang tag, không
        # có URL phân trang tĩnh đáng tin cậy -> chỉ crawl được trang đầu.
        paginate_template=None,
        max_pages=1,
    ),
    "thanhnien": NewsSource(
        key="thanhnien",
        display_name="Thanh Niên",
        listing_urls=(
            "https://thanhnien.vn/world-cup-2026-tags486068.html",
            "https://thanhnien.vn/the-thao/world-cup-2026.htm",
        ),
        # thanhnien.vn/<slug>-<id số>.htm
        article_url_pattern=re.compile(r"^https://thanhnien\.vn/[a-z0-9\-]+-\d{9,18}\.htm$"),
        paginate_template=None,
        max_pages=1,
    ),
}


class FetchError(RuntimeError):
    pass


def fetch_html(url: str, timeout: int = 20) -> str:
    response = _SESSION.get(url, timeout=timeout)
    response.raise_for_status()
    # Cả 3 báo đều publish UTF-8 (đã xác minh qua header Content-Type khi khảo
    # sát), nhưng requests đôi khi tự đoán sai encoding (fallback về
    # ISO-8859-1 theo default HTTP cũ) nếu server không trả charset rõ ràng
    # cho traffic không giống trình duyệt -> gây lỗi mojibake tiếng Việt
    # (title/slug/content/keywords bị lỗi ký tự). Ép cứng UTF-8 cho chắc.
    response.encoding = "utf-8"
    return response.text


# ---------------------------------------------------------------------------
# 1) Khám phá link bài viết từ trang danh sách
# ---------------------------------------------------------------------------

def extract_article_links(html: str, source: NewsSource, base_url: Optional[str] = None) -> list[str]:
    """
    base_url: URL của chính trang danh sách đang parse, dùng để resolve các
    href tương đối (VD Thanh Niên phát ra href="/xac-dinh-tran-dau...htm"
    thay vì URL tuyệt đối) thành URL đầy đủ trước khi so khớp regex. Không
    truyền base_url thì bỏ qua mọi href tương đối (an toàn nhưng có thể sót).
    """
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].split("#")[0].strip()
        if not href:
            continue
        if base_url:
            href = urljoin(base_url, href)
        if source.article_url_pattern.match(href) and href not in seen:
            seen.add(href)
            links.append(href)
    return links


def discover_article_urls(source: NewsSource, max_pages: Optional[int] = None, timeout: int = 20) -> list[str]:
    """Fetch (các) trang danh sách + phân trang (nếu site hỗ trợ) và gom hết link bài viết."""
    pages_to_try = max_pages if max_pages is not None else source.max_pages
    all_urls: list[str] = []
    seen: set[str] = set()

    urls_to_fetch = list(source.listing_urls)
    if source.paginate_template:
        for page in range(2, pages_to_try + 1):
            urls_to_fetch.append(source.paginate_template.format(page=page))

    for listing_url in urls_to_fetch:
        try:
            html = fetch_html(listing_url, timeout=timeout)
        except (requests.RequestException, OSError) as exc:
            print(f"[vn-news-source]   Lỗi tải trang danh sách {listing_url}: {exc}")
            continue
        found = extract_article_links(html, source, base_url=listing_url)
        if not found:
            print(f"[vn-news-source]   Cảnh báo: {listing_url} tải được nhưng không tìm thấy link bài viết nào khớp pattern")
        for url in found:
            if url not in seen:
                seen.add(url)
                all_urls.append(url)

    return all_urls


# ---------------------------------------------------------------------------
# 2) Trích xuất nội dung 1 bài viết
# ---------------------------------------------------------------------------

def _meta_content(soup: BeautifulSoup, *names: str) -> Optional[str]:
    for name in names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


def _parse_published_at(soup: BeautifulSoup) -> Optional[datetime]:
    raw = _meta_content(soup, "article:published_time", "pubdate", "article:modified_time")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _is_noise(tag: Tag) -> bool:
    for ancestor in tag.parents:
        if not isinstance(ancestor, Tag):
            continue
        if ancestor.name in NOISE_ANCESTOR_TAGS:
            return True
        classes = " ".join(ancestor.get("class", [])) + " " + (ancestor.get("id") or "")
        classes_lower = classes.lower()
        if any(keyword in classes_lower for keyword in NOISE_CLASS_KEYWORDS):
            return True
    return False


def _is_boilerplate(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in BOILERPLATE_PARAGRAPH_MARKERS)


def _extract_content(soup: BeautifulSoup, min_paragraph_len: int = 40) -> str:
    """
    Heuristic tổng quát (không phụ thuộc class CSS riêng của từng báo):
    nhóm các thẻ <p> "thật" (đủ dài, không nằm trong nav/footer/quảng cáo/box
    liên quan) theo thẻ cha trực tiếp, chọn nhóm có tổng độ dài text lớn nhất
    - đó gần như luôn chính là khối nội dung bài viết. Sau khi chọn nhóm, lọc
    tiếp từng đoạn theo BOILERPLATE_PARAGRAPH_MARKERS để loại các đoạn quảng
    cáo cố định (VD "Tuổi Trẻ Sao") dù chúng nằm chung thẻ cha với nội dung
    bài thật.
    """
    candidates: dict[int, list[str]] = {}
    for p in soup.find_all("p"):
        text = p.get_text(" ", strip=True)
        if len(text) < min_paragraph_len:
            continue
        if _is_noise(p) or _is_boilerplate(text):
            continue
        parent = p.parent
        if parent is None:
            continue
        candidates.setdefault(id(parent), []).append(text)

    if not candidates:
        return ""

    best_group = max(candidates.values(), key=lambda paras: sum(len(t) for t in paras))
    return "\n\n".join(best_group)


def is_world_cup_relevant(title: str, summary: str, content: str) -> bool:
    """
    Trang danh sách (đặc biệt Thanh Niên) thường chèn thêm link "tin nổi
    bật"/"tin khác" ở sidebar không liên quan chủ đề trang - các link đó vẫn
    khớp regex URL bài viết nên bị crawler nhặt nhầm (VD tin chứng khoán, tin
    casino, tin bóng đá CLB không dính World Cup). Lọc lại bằng nội dung
    thật: bài phải nhắc "world cup" ở đâu đó trong title/summary/content mới
    được lưu.
    """
    combined = f"{title} {summary} {content}".lower()
    return "world cup" in combined


def detect_world_cup_year(*texts: str, default_year: Optional[int] = None) -> Optional[int]:
    """Tìm năm World Cup được nhắc tới nhiều nhất trong các đoạn text đưa vào."""
    combined = " ".join(t for t in texts if t)
    counts: dict[int, int] = {}
    for year in WORLD_CUP_YEARS:
        hits = len(re.findall(rf"\b{year}\b", combined))
        if hits:
            counts[year] = hits
    if not counts:
        return default_year
    return max(counts.items(), key=lambda item: (item[1], item[0]))[0]


def parse_article(html: str, url: str, source: NewsSource, default_wc_year: Optional[int] = None) -> dict:
    soup = BeautifulSoup(html, "lxml")

    title = _meta_content(soup, "og:title") or (soup.title.get_text(strip=True) if soup.title else "")
    summary = _meta_content(soup, "og:description", "description") or ""
    thumbnail_url = _meta_content(soup, "og:image") or ""
    keywords_raw = _meta_content(soup, "keywords", "news_keywords") or ""
    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    published_at = _parse_published_at(soup)
    content = _extract_content(soup) or summary

    world_cup_year = detect_world_cup_year(title, summary, content, default_year=default_wc_year)

    return {
        "title": title.strip(),
        "summary": summary.strip(),
        "content": content.strip(),
        "url": url,
        "source": source.display_name,
        "published_at": published_at,
        "thumbnail_url": thumbnail_url,
        "keywords": keywords,
        "world_cup_year": world_cup_year,
    }
