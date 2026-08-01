import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _json_serializer(obj) -> str:
    # Mặc định SQLAlchemy/psycopg2 dùng json.dumps(ensure_ascii=True) khi ghi
    # cột JSON, khiến mọi ký tự có dấu (VD tiếng Việt) bị escape thành dạng
    # "\u1ed9" thay vì lưu literal UTF-8. Ghi đè để giữ nguyên ký tự gốc.
    return json.dumps(obj, ensure_ascii=False)


engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {},
    pool_pre_ping=True,
    json_serializer=_json_serializer,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)