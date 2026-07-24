# Tài liệu dự án: Hệ thống lưu trữ, thu thập thông tin World Cup

## 1. Tổng quan dự án

Dự án này là một hệ thống backend dùng Python để:
- thu thập dữ liệu World Cup từ nguồn trực tuyến và file fixture nội bộ,
- lưu trữ dữ liệu vào cơ sở dữ liệu,
- cung cấp API để truy vấn thông tin về giải đấu, đội bóng, cầu thủ, trận đấu, bảng xếp hạng và thống kê.

### Công nghệ chính
- Python 3.10+
- FastAPI: xây dựng API
- SQLAlchemy: ORM và thao tác database
- Alembic: quản lý migration database
- Pydantic: validate schema và cấu hình môi trường
- PostgreSQL (mặc định trong file cấu hình môi trường)

### Mục tiêu chức năng hiện tại
- Quản lý dữ liệu World Cup
- Quản lý thông tin đội bóng
- Quản lý thông tin trận đấu
- Quản lý bảng xếp hạng
- Quản lý thống kê và dữ liệu tin tức
- Crawler để thu thập dữ liệu từ FIFA và các nguồn khác

---

## 2. Cấu trúc thư mục và vai trò

### Thư mục gốc
- `alembic/`: chứa các file migration và cấu hình Alembic để thay đổi schema database.
- `alembic.ini`: file cấu hình Alembic.
- `app/`: toàn bộ mã nguồn chính của hệ thống.
- `data/`: thư mục chứa dữ liệu crawl hoặc dữ liệu đầu ra phụ trợ.
- `tests/`: các test kiểm thử cho crawler và logic chính.
- `fifa_matches_page.html`: file HTML fixture dùng để test crawler offline.
- `world_cup.db`: file database SQLite có thể tồn tại trong quá trình phát triển cũ.

### Thư mục `app/`
Đây là trung tâm của dự án.

#### `app/main.py`
- File entry point của ứng dụng FastAPI.
- Khởi tạo app, đăng ký các router và triển khai endpoint `/` và `/health`.

#### `app/core/`
- `config.py`: đọc cấu hình môi trường từ file `.env` hoặc `app/.env`.
- Dùng để cấu hình `APP_NAME`, `APP_ENV`, `DATABASE_URL`.

#### `app/crawler/`
- Chứa toàn bộ logic crawler và CLI để thu thập dữ liệu.
- `cli.py`: file chính của crawler.
  - parse HTML, trích xuất dữ liệu match từ payload JSON embedded,
  - xây dựng team map, match record, standing rows,
  - gọi repository để lưu dữ liệu vào DB.

#### `app/database/`
- `session.py`: khởi tạo engine SQLAlchemy, session factory và Base class cho ORM.
- Đây là lớp kết nối với database.

#### `app/dependencies/`
- `database.py`: dependency injection cho FastAPI để lấy DB session.

#### `app/models/`
Chứa các ORM model tương ứng với bảng trong database.
- `world_cup.py`: model giải đấu World Cup
- `team.py`: model đội bóng
- `player.py`: model cầu thủ
- `matches.py`: model trận đấu
- `standings.py`: model bảng xếp hạng
- `goals.py`: model bàn thắng
- `cards.py`: model thẻ phạt
- `news.py`: model tin tức

#### `app/repositories/`
Chứa lớp repository dùng để thao tác dữ liệu với database.
- `world_cup_repository.py`: CRUD cho World Cup
- `team_repository.py`: CRUD cho Team
- `player_repository.py`: CRUD cho Player
- `match_repository.py`: CRUD cho Match
- `standing_repository.py`: CRUD cho Standing
- `statistics_repository.py`: truy vấn thống kê
- `news_repository.py`: CRUD cho News

#### `app/services/`
Chứa business logic tầng service.
- `team_service.py`
- `world_cup_service.py`
- `player_service.py`
- `match_service.py`
- `standing_service.py`
- `statistics_service.py`
- `news_service.py`

#### `app/schemas/`
Chứa các Pydantic schema dùng cho request/response và validation.
- `team.py`
- `world_cup.py`
- `match.py`
- `standing.py`
- `statistics.py`
- `player.py`
- `news.py`

#### `app/routers/`
Chứa các router FastAPI, ánh xạ endpoint HTTP.
- `team_router.py`: endpoints về đội bóng
- `world_cup_router.py`: endpoints về giải đấu
- `player_router.py`: endpoints về cầu thủ
- `match_router.py`: endpoints về trận đấu
- `standing_router.py`: endpoints về bảng xếp hạng
- `statistics_router.py`: endpoints về thống kê
- `news_router.py`: endpoints về tin tức

---

## 3. Các tính năng chính hiện có

### 3.1 API backend
Hệ thống hiện có API cho các nhóm dữ liệu chính:
- đội bóng
- giải đấu World Cup
- cầu thủ
- trận đấu
- bảng xếp hạng
- thống kê
- tin tức

### 3.2 Crawler dữ liệu
Crawler có khả năng:
- đọc nội dung HTML từ URL hoặc file fixture nội bộ,
- parse dữ liệu match từ payload JSON embedded,
- xây dựng cấu trúc dữ liệu team, match, standings,
- lưu vào database.

### 3.3 Quản lý dữ liệu bằng ORM
Dữ liệu được lưu vào database thông qua SQLAlchemy thay vì thao tác trực tiếp SQL.

### 3.4 Kiểm thử
Dự án có test cho crawler parsing. Test hiện tại chạy thành công.

---

## 4. Luồng hoạt động của hệ thống

### Luồng API
1. Client gọi một endpoint qua FastAPI.
2. Router nhận request.
3. Service xử lý nghiệp vụ.
4. Repository tương tác với database.
5. Kết quả trả về cho client dưới dạng JSON.

### Luồng crawler
1. CLI crawler nhận tham số entity và nguồn dữ liệu.
2. Tải HTML hoặc đọc fixture nội bộ.
3. Trích xuất dữ liệu bằng parser.
4. Xây dựng record cho team/match/standing.
5. Gọi repository lưu vào database.

---

## 5. Các endpoint chính (hiện tại)

### Health check
- `GET /health`
- Trả về trạng thái server và kết nối DB.

### Teams
- `GET /teams/`
- `GET /teams/{team_id}`
- `POST /teams/`

### World Cups
- `GET /world-cups/`
- `GET /world-cups/{world_cup_id}`

### Standings
- `GET /standings/world-cup/{world_cup_id}`
- `GET /standings/world-cup/{world_cup_id}/groups/{group_name}`

### Statistics
- `GET /statistics/teams/most-titles`
- `GET /statistics/players/top-scorers`
- `GET /statistics/matches/most-goals`
- `GET /statistics/matches/most-cards`
- `GET /statistics/players/most-appearances`

> Ghi chú: một số router có thể chưa được triển khai đầy đủ cho tất cả entity, nhưng cơ cấu đã sẵn sàng và đang được mở rộng.

---

## 6. Hướng dẫn cài đặt môi trường

### Bước 1: Cài Python
Khuyến nghị dùng Python 3.10 trở lên.

### Bước 2: Tạo virtual environment
```powershell
cd D:\Projects\thuc-tap-vccorp\he-thong-luu-tru-thong-tin-world-cup\worldcup_scraper_thuc_tap_vccorp
python -m venv .venv
```

### Bước 3: Kích hoạt môi trường ảo
```powershell
.\.venv\Scripts\Activate.ps1
```

### Bước 4: Cài dependency cần thiết
Các package chính thường dùng trong dự án:
```powershell
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings psycopg2-binary alembic
```

### Bước 5: Cấu hình database
File cấu hình môi trường hiện tại nằm tại:
- `app/.env`

Nội dung ví dụ:
```env
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/worldcup_db
APP_NAME=Hệ thống lưu trữ, thu thập thông tin về World Cup
APP_ENV=development
```

> Nếu dùng PostgreSQL, hãy đảm bảo database `worldcup_db` đã được tạo trước.

---

## 7. Hướng dẫn chạy dự án

### 7.1 Chạy API server
```powershell
cd D:\Projects\thuc-tap-vccorp\he-thong-luu-tru-thong-tin-world-cup\worldcup_scraper_thuc_tap_vccorp
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Sau khi chạy, mở:
- `http://127.0.0.1:8000/docs` để xem Swagger UI
- `http://127.0.0.1:8000/health` để kiểm tra trạng thái server

### 7.2 Chạy crawler
```powershell
cd D:\Projects\thuc-tap-vccorp\he-thong-luu-tru-thong-tin-world-cup\worldcup_scraper_thuc_tap_vccorp
.\.venv\Scripts\Activate.ps1
python -m app.crawler.cli sync --entity all --output data/crawl
```

### 7.3 Chạy test
```powershell
cd D:\Projects\thuc-tap-vccorp\he-thong-luu-tru-thong-tin-world-cup\worldcup_scraper_thuc_tap_vccorp
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -p "test_*.py"
```

---

## 8. Hướng dẫn dùng Alembic
Nếu cần tạo migration mới:
```powershell
alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

## 9. Tình trạng hiện tại của dự án

### Đã hoàn thành tốt
- Cấu trúc backend cơ bản đã có
- API router và service layer đã được thiết kế rõ ràng
- Crawler có khả năng parse dữ liệu thực tế từ fixture FIFA
- Có test regression cho crawler

### Đang tiếp tục phát triển
- Hoàn thiện lưu trữ dữ liệu cho các entity còn thiếu như goals, cards, players, news
- Kiểm thử end-to-end từ crawler tới database và API

### Kết quả kiểm thử mới nhất
Đã chạy lệnh:
```powershell
python -m unittest discover -s tests -p "test_*.py"
```
Kết quả: 3 tests chạy thành công, không lỗi.

---

## 10. Gợi ý phát triển tiếp theo
- Hoàn thiện crawler cho nhiều nguồn tin khác nhau
- Bổ sung endpoint cho CRUD đầy đủ hơn cho từng entity
- Tích hợp dữ liệu thực tế từ FIFA và nguồn tin thể thao
- Thêm xử lý lỗi và logging cho crawler
- Tối ưu hóa query thống kê và bảng xếp hạng

---

## 11. Mẹo làm việc với dự án
- Khi sửa code, ưu tiên cập nhật cả model, repository, service và router nếu cần thay đổi API.
- Khi thêm dữ liệu crawl mới, nên viết test trước rồi mới mở rộng parser.
- Đối với dữ liệu lớn, nên kiểm tra DB trước khi chạy crawler nhiều lần để tránh duplicate không mong muốn.
