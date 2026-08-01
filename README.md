# Hệ thống lưu trữ thông tin World Cup

Backend hệ thống thu thập, lưu trữ và cung cấp API dữ liệu World Cup: kết quả
trận đấu, bảng xếp hạng, thông tin đội tuyển qua các kỳ giải (1930–2026), và
tin tức bóng đá tiếng Việt liên quan.

---

## Mục lục

- [1. Tổng quan](#1-tổng-quan)
- [2. Kiến trúc & công nghệ](#2-kiến-trúc--công-nghệ)
- [3. Cấu trúc thư mục](#3-cấu-trúc-thư-mục)
- [4. Mô hình dữ liệu](#4-mô-hình-dữ-liệu)
- [5. Cài đặt](#5-cài-đặt)
- [6. Crawler dữ liệu](#6-crawler-dữ-liệu)
- [7. API](#7-api)
- [8. Kiểm thử](#8-kiểm-thử)
- [9. Giới hạn đã biết](#9-giới-hạn-đã-biết)
- [10. Định hướng phát triển](#10-định-hướng-phát-triển)

---

## 1. Tổng quan

Hệ thống gồm 2 phần chính:

1. **Crawler** — thu thập dữ liệu từ các nguồn mở/báo chí, chuẩn hoá và ghi
   vào PostgreSQL:
   - Dữ liệu trận đấu & bảng xếp hạng lịch sử toàn bộ 23 kỳ World Cup
     (1930–2026) từ [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json)
     (nguồn mở, public domain).
   - Tin tức bóng đá/World Cup tiếng Việt từ VnExpress, Tuổi Trẻ, Thanh Niên.
2. **REST API** (FastAPI) — truy vấn dữ liệu đã crawl: đội tuyển, trận đấu,
   bảng xếp hạng, tin tức, thống kê.

## 2. Kiến trúc & công nghệ

| Thành phần | Công nghệ |
|---|---|
| API framework | FastAPI |
| ORM | SQLAlchemy 2.0 (Mapped/mapped_column) |
| Database | PostgreSQL |
| Migration | Alembic |
| Validation / schema | Pydantic v2 |
| HTTP client (crawler) | requests |
| HTML parsing (crawler) | BeautifulSoup4 + lxml |
| Test | unittest (thư viện chuẩn Python) |

Kiến trúc theo layer rõ ràng, tách biệt trách nhiệm:

```
Router (FastAPI endpoint)
   → Service (business logic)
      → Repository (truy vấn DB qua SQLAlchemy)
         → Model (ORM, ánh xạ bảng)
```

Schema Pydantic (`app/schemas/`) dùng riêng cho request/response của API,
tách biệt hoàn toàn với Model ORM (`app/models/`).

## 3. Cấu trúc thư mục

```
app/
├── main.py                    # Khởi tạo FastAPI app, đăng ký router
├── core/config.py             # Cấu hình (đọc từ .env qua pydantic-settings)
├── database/
│   ├── session.py             # Engine, SessionLocal
│   └── base.py                # Declarative Base, import tất cả model để đăng ký
├── models/                    # SQLAlchemy ORM models
├── schemas/                   # Pydantic request/response schemas
├── repositories/               # Tầng truy vấn DB
├── services/                  # Tầng business logic
├── routers/                   # FastAPI endpoints
├── dependencies/               # FastAPI dependencies (VD get_db)
└── crawler/
    ├── sources/
    │   ├── openfootball_source.py   # Fetch/parse dữ liệu trận đấu & BXH lịch sử
    │   └── vn_news_source.py        # Fetch/parse tin tức tiếng Việt
    ├── sync_openfootball.py         # CLI đồng bộ trận đấu/BXH vào DB
    ├── sync_vn_news.py              # CLI đồng bộ tin tức vào DB
    └── cli.py                       # Crawler World Cup 2026 từ trang FIFA (bổ sung)

alembic/versions/              # Lịch sử migration DB
tests/                         # Unit test + integration test (33 test)
```

## 4. Mô hình dữ liệu

5 bảng chính:

| Bảng | Mô tả | Quan hệ |
|---|---|---|
| `world_cups` | Mỗi kỳ World Cup: năm, nước chủ nhà, đội vô địch/á quân | 1—N với `matches`, `standings`, `news` |
| `teams` | Đội tuyển quốc gia (giữ riêng biệt các thực thể lịch sử gián đoạn, VD Tây Đức ≠ Đức, Liên Xô ≠ Nga) | N—N với `world_cups` qua `matches`/`standings` |
| `matches` | Từng trận đấu: 2 đội, tỉ số, hiệp phụ, luân lưu, vòng đấu, sân/thành phố | N—1 với `world_cups`, `teams` (2 FK: `team_1_id`, `team_2_id`) |
| `standings` | Bảng xếp hạng theo bảng đấu của từng kỳ | N—1 với `world_cups`, `teams` |
| `news` | Tin tức đã crawl, gắn với 1 kỳ World Cup cụ thể | N—1 với `world_cups` |

Chi tiết migration:
- `ef88325b1a6f` — khởi tạo toàn bộ bảng
- `08261c197c69` — vá lỗi thiếu `server_default` cho cột `created_at`/`updated_at`
- `286ff9a553b3` — loại bỏ 2 cột `attendance`/`referee` khỏi `matches` và loại
  bỏ hẳn 3 bảng `players`, `goals`, `cards` (thu hẹp phạm vi dữ liệu về đúng
  yêu cầu: trận đấu, BXH, tin tức)

## 5. Cài đặt

**Yêu cầu:** Python 3.10+, PostgreSQL đang chạy.

```powershell
# 1. Clone / giải nén project, tạo virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Cài dependency
pip install -r requirements.txt

# 3. Tạo file cấu hình local từ bản mẫu (KHÔNG commit 2 file này lên git,
#    đã có trong .gitignore vì chứa mật khẩu DB thật)
copy app\.env.example app\.env
copy alembic.ini.example alembic.ini
#    Sau đó sửa DATABASE_URL trong 2 file trên cho khớp Postgres máy bạn

# 4. Khởi tạo schema
alembic upgrade head

# 5. Chạy API
uvicorn app.main:app --reload
```

API mặc định chạy tại `http://127.0.0.1:8000`, tài liệu OpenAPI tự sinh tại
`http://127.0.0.1:8000/docs`.

Kiểm tra kết nối DB nhanh: `GET /health`.

## 6. Crawler dữ liệu

### 6.1. Trận đấu & bảng xếp hạng lịch sử (1930–2026)

Nguồn: [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json)
(public domain, không cần API key).

```powershell
# Xem trước, không ghi DB
python -m app.crawler.sync_openfootball --years all --dry-run

# Chạy thật — nạp toàn bộ 23 kỳ
python -m app.crawler.sync_openfootball --years all

# Hoặc theo năm/khoảng năm cụ thể
python -m app.crawler.sync_openfootball --years 2018,2022
python -m app.crawler.sync_openfootball --years 1990-2010
```

Script **idempotent** — chạy lại nhiều lần sẽ cập nhật (`UPDATE`) thay vì tạo
bản ghi trùng, dựa trên khoá tự nhiên (`world_cup_id + team_1_id + team_2_id
+ match_date + stage` cho trận đấu).

### 6.2. Tin tức tiếng Việt (VnExpress, Tuổi Trẻ, Thanh Niên)

```powershell
python -m app.crawler.sync_vn_news --sources all --dry-run
python -m app.crawler.sync_vn_news --sources all
```

Crawler tự nhận diện năm World Cup được nhắc tới trong bài để gán đúng
`world_cup_id`, tự lọc bỏ bài không thực sự liên quan World Cup, và loại các
đoạn quảng cáo/nội bộ toà soạn cố định khỏi nội dung trích xuất. **Phải chạy
crawler trận đấu (6.1) trước** để bảng `world_cups` có dữ liệu — nếu không,
bài viết về năm chưa tồn tại trong DB sẽ bị bỏ qua.

Chi tiết đầy đủ (tham số CLI, cách hoạt động, giới hạn đã biết) xem
[`PROJECT_DOCUMENTATION.md`](PROJECT_DOCUMENTATION.md) mục 12–13.

## 7. API

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/teams` | Danh sách đội tuyển |
| GET | `/teams/{id}` | Chi tiết 1 đội |
| POST | `/teams` | Tạo đội mới |
| GET | `/world-cups` | Danh sách các kỳ World Cup |
| GET | `/world-cups/{id}` | Chi tiết 1 kỳ |
| GET | `/world-cups/year/{year}` | Tra theo năm |
| POST | `/world-cups` | Tạo kỳ World Cup mới |
| GET | `/matches` | Danh sách trận đấu |
| GET | `/matches/{id}` | Chi tiết 1 trận |
| GET | `/matches/world-cup/{world_cup_id}` | Trận đấu theo kỳ World Cup |
| POST | `/matches` | Tạo trận đấu |
| GET | `/standings/world-cup/{world_cup_id}` | BXH toàn bộ các bảng của 1 kỳ |
| GET | `/standings/world-cup/{world_cup_id}/groups/{group_name}` | BXH 1 bảng cụ thể |
| GET | `/news` | Danh sách tin tức |
| GET | `/news/{id}` | Chi tiết 1 bài |
| GET | `/news/world-cup/{world_cup_id}` | Tin tức theo kỳ World Cup |
| POST | `/news` | Tạo bản ghi tin tức |
| GET | `/statistics/teams/most-titles` | Đội vô địch nhiều nhất |
| GET | `/statistics/matches/most-goals` | Trận đấu nhiều bàn thắng nhất |
| GET | `/health` | Kiểm tra tình trạng kết nối DB |

Tài liệu tương tác đầy đủ (thử trực tiếp từng endpoint): `/docs` (Swagger UI)
hoặc `/redoc`.

## 8. Kiểm thử

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

33 test, bao phủ:
- Logic parse dữ liệu openfootball (điểm số, hiệp phụ, luân lưu, các định
  dạng dữ liệu khác nhau qua từng năm, ca đặc biệt World Cup 1950)
- Logic parse tin tức (trích xuất link bài viết, nội dung, lọc boilerplate,
  lọc bài không liên quan World Cup)
- Test tích hợp ghi DB thật (SQLite in-memory) cho cả 2 crawler
- Test crawler World Cup 2026 (FIFA) có sẵn từ trước

## 9. Giới hạn đã biết

- `teams.fifa_code`/`teams.continent` chỉ có giá trị cho các kỳ 2014, 2018,
  2026 (nguồn dữ liệu mở không cung cấp cho các năm khác).
- Cờ `standings.qualified` là suy luận (mặc định top 2/bảng đi tiếp), có thể
  không chính xác với các kỳ dùng thể thức đặc biệt (VD vòng bảng thứ hai ở
  1974/1978).
- Crawler tin tức không trích xuất được tên tác giả bài viết đáng tin cậy từ
  mọi trang — hiện gán tạm bằng tên toà soạn.
- Tuổi Trẻ/Thanh Niên chỉ crawl được trang danh sách đầu tiên do cơ chế tải
  thêm bài bằng JavaScript (không có URL phân trang tĩnh).
- Không lưu trữ dữ liệu cầu thủ, bàn thắng, thẻ phạt (đã loại khỏi phạm vi dự
  án — xem migration `286ff9a553b3`).

## 10. Định hướng phát triển

- Bổ sung nguồn dữ liệu thẻ phạt (Wikipedia/RSSSF) cho các kỳ gần đây.
- Cải thiện trích xuất tên tác giả tin tức theo từng báo.
- Thêm phân trang thật cho API danh sách (hiện trả toàn bộ kết quả).
- Lên lịch crawl định kỳ (cron/Celery Beat) thay vì chạy tay.
