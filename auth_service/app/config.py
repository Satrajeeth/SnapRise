from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SnapRise Auth Service"
    debug: bool = True
    auth_jwt_secret: str = "super-secret-auth-key"
    allowed_origins: str = "*"

    database_url: str = "postgresql+asyncpg://app:password@snaprise_postgres:5432/auth_db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
