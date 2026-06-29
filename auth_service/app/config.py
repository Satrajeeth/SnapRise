from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SnapRise Auth Service"
    debug: bool = True
    auth_jwt_secret: str = "super-secret-auth-key"
    # Access tokens are short-lived; refresh tokens are long-lived and used
    # only to mint new access tokens via /auth/jwt/refresh.
    auth_jwt_access_lifetime_seconds: int = 3600  # 1 hour
    auth_jwt_refresh_lifetime_seconds: int = 60 * 60 * 24 * 30  # 30 days
    allowed_origins: str = "*"

    database_url: str = "postgresql+asyncpg://app:password@postgres:5432/auth_db"
    reset_password_redirect_url: str = "http://localhost:3000/reset-password"
    password_reset_delivery_mode: Literal["console", "smtp"] = "console"

    smtp_host: str = "smtp"
    smtp_port: int = 25
    smtp_from_email: str = "no-reply@snaprise.local"
    smtp_timeout_seconds: int = 10
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False
    smtp_use_ssl: bool = False

    otp_proof_secret: str = "secret"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
