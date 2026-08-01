"""
CLI crawl tin tức bóng đá / World Cup tiếng Việt (VnExpress, Tuổi Trẻ, Thanh Niên)
và đồng bộ vào bảng `news`.

Cách chạy (từ thư mục gốc project, đã kích hoạt venv, đã cài
beautifulsoup4+lxml trong requirements.txt):

    # Xem trước sẽ crawl được gì, KHÔNG ghi DB
    python -m app.crawler.sync_vn_news --sources all --dry-run

    # Crawl thật, mặc định gán năm World Cup không nhận diện được vào 2026
    python -m app.crawler.sync_vn_news --sources all

    # Chỉ 1 nguồn, giới hạn số bài, tăng độ trễ giữa các request cho lịch sự
    python -m app.crawler.sync_vn_news --sources vnexpress --limit 20 --delay 1.5

Lưu ý:
- Tuổi Trẻ và Thanh Niên hiện chỉ crawl được trang danh sách ĐẦU TIÊN (các
  trang này tải thêm bài bằng nút "Xem thêm" chạy JS/AJAX, không có URL phân
  trang tĩnh để crawl tiếp bằng requests thông thường).
- VnExpress hỗ trợ phân trang qua --pages (mặc định 5 trang).
"""
from __future__ import annotations

import argparse
import os
import re
import time
import unicodedata
from datetime import datetime, timezone
from typing import Optional

from app.crawler.sources.vn_news_source import (
    NEWS_SOURCES,
    discover_article_urls,
    fetch_html,
    is_world_cup_relevant,
    parse_article,
)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "bai-viet"


def sync_source(db, source_key: str, pages: int, limit: int, delay: float, default_wc_year: int, stats: dict) -> None:
    from app.models.news import News
    from app.models.world_cup import WorldCup

    source = NEWS_SOURCES[source_key]
    print(f"[vn-news-sync] Đang tìm bài viết từ {source.display_name}...")
    article_urls = discover_article_urls(source, max_pages=pages)
    if limit:
        article_urls = article_urls[:limit]
    print(f"[vn-news-sync]   Tìm thấy {len(article_urls)} link bài viết")

    for url in article_urls:
        existing = db.query(News).filter(News.url == url).first()
        if existing:
            stats["skipped_existing"] += 1
            continue

        try:
            html = fetch_html(url)
        except Exception as exc:  # noqa: BLE001 - crawler không nên chết vì 1 bài lỗi
            print(f"[vn-news-sync]   Lỗi tải {url}: {exc}")
            stats["fetch_errors"] += 1
            continue

        parsed = parse_article(html, url, source, default_wc_year=default_wc_year)
        if not parsed["title"] or not parsed["content"]:
            stats["skipped_empty"] += 1
            continue

        if not is_world_cup_relevant(parsed["title"], parsed["summary"], parsed["content"]):
            stats["skipped_not_world_cup"] += 1
            continue

        world_cup = db.query(WorldCup).filter(WorldCup.year == parsed["world_cup_year"]).first()
        if not world_cup:
            # Chưa có World Cup năm này trong DB (chưa chạy sync_openfootball
            # cho năm đó) -> bỏ qua bài này thay vì ghi world_cup_id sai.
            stats["skipped_unknown_world_cup"] += 1
            continue

        now = datetime.now(timezone.utc)
        news = News(
            title=parsed["title"][:500],
            slug=slugify(parsed["title"])[:500],
            summary=parsed["summary"] or parsed["title"],
            content=parsed["content"],
            url=parsed["url"],
            source=parsed["source"],
            author=parsed["source"],  # xem lưu ý ở README: không trích xuất được tên tác giả đáng tin cậy
            published_at=parsed["published_at"] or now,
            crawled_at=now,
            world_cup_id=world_cup.id,
            thumbnail_url=parsed["thumbnail_url"],
            keywords=parsed["keywords"],
        )
        db.add(news)
        stats["created"] += 1
        time.sleep(delay)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Crawl tin tức World Cup tiếng Việt vào bảng news")
    parser.add_argument("--sources", default="all", help="'all' hoặc danh sách 'vnexpress,tuoitre,thanhnien'")
    parser.add_argument("--pages", type=int, default=None, help="Số trang danh sách tối đa mỗi nguồn (mặc định theo cấu hình từng nguồn)")
    parser.add_argument("--limit", type=int, default=0, help="Giới hạn số bài crawl mỗi nguồn (0 = không giới hạn)")
    parser.add_argument("--delay", type=float, default=1.0, help="Số giây nghỉ giữa các request bài viết (lịch sự với server)")
    parser.add_argument("--default-wc-year", type=int, default=2026, help="Năm World Cup gán mặc định nếu không nhận diện được năm trong bài")
    parser.add_argument("--db-url", default=None, help="Ghi đè DATABASE_URL")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in link/số liệu, không ghi DB")
    args = parser.parse_args(argv)

    if args.db_url:
        os.environ["DATABASE_URL"] = args.db_url

    source_keys = list(NEWS_SOURCES.keys()) if args.sources.strip().lower() == "all" else [
        s.strip() for s in args.sources.split(",") if s.strip()
    ]
    unknown = [s for s in source_keys if s not in NEWS_SOURCES]
    if unknown:
        raise SystemExit(f"Nguồn không hợp lệ: {unknown}. Các nguồn hỗ trợ: {list(NEWS_SOURCES.keys())}")

    if args.dry_run:
        for key in source_keys:
            source = NEWS_SOURCES[key]
            urls = discover_article_urls(source, max_pages=args.pages)
            if args.limit:
                urls = urls[: args.limit]
            print(f"{source.display_name}: {len(urls)} bài viết tìm thấy")
            for url in urls[:5]:
                print(f"  - {url}")
        return 0

    from app.database.base import Base  # noqa: F401
    from app.database.session import SessionLocal

    stats = {
        "created": 0,
        "skipped_existing": 0,
        "skipped_empty": 0,
        "skipped_not_world_cup": 0,
        "skipped_unknown_world_cup": 0,
        "fetch_errors": 0,
    }

    db = SessionLocal()
    try:
        for key in source_keys:
            sync_source(
                db,
                key,
                pages=args.pages if args.pages is not None else NEWS_SOURCES[key].max_pages,
                limit=args.limit,
                delay=args.delay,
                default_wc_year=args.default_wc_year,
                stats=stats,
            )
            db.commit()
        print("[vn-news-sync] Hoàn tất.")
        for k, v in stats.items():
            print(f"  {k}: {v}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
