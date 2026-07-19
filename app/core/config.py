from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    APP_NAME: str = "World Cup API"
    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./world_cup.db"

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", ROOT_DIR / "app" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
