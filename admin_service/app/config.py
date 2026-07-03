from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="SnapRise Admin Service", alias="APP_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")

    database_url: str = Field(..., alias="DATABASE_URL")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")

    api_prefix: str = Field(default="/v1", alias="API_PREFIX")
    # Comma-separated string (parsed in main.py). Kept as a plain str — same as
    # auth_service — because pydantic-settings tries to JSON-decode List[str] env
    # values before validators run, which breaks on a bare comma string.
    allowed_origins: str = Field(default="*", alias="ALLOWED_ORIGINS")

    # Shared auth: admin_service does not own users — it verifies the access
    # tokens auth_service issues. These three must match auth_service so the
    # signature/audience check passes, and so the `is_superuser` claim (embedded
    # by auth_service's SnapRiseJWTStrategy) can be trusted.
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_audience: str = Field(default="fastapi-users:auth", alias="JWT_AUDIENCE")

    # Shared secret protecting the internal lead-ingest endpoint. board_service's
    # outbox drainer presents this; it is NOT a user-facing credential and is only
    # reachable on the compose network. Compared in constant time.
    admin_ingest_secret: str = Field(..., alias="ADMIN_INGEST_SECRET")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        if value not in allowed:
            raise ValueError(f"Invalid environment: {value}. Allowed: {sorted(allowed)}")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
