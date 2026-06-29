from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="SnapRise Board Service", alias="APP_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")

    database_url: str = Field(..., alias="DATABASE_URL")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")

    api_prefix: str = Field(default="/v1", alias="API_PREFIX")
    allowed_origins: List[str] = Field(default=["*"], alias="ALLOWED_ORIGINS")

    #Security
    #Default key for development only (Fernet 32-byte base64)
    encryption_key: str = Field(
        default="3-yHjX8W-k-q_M-S6kY_Uv_f_S6-S_L_Z-Y8-k-X8-I=",
        alias="ENCRYPTION_KEY"
    )

    # Must match the auth_service signing secret (auth_service AUTH_JWT_SECRET),
    # since the board service verifies the JWTs that the auth service issues.
    jwt_secret: str = Field(default="super-secret-auth-key", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    # fastapi-users embeds this audience claim in login tokens; it must be
    # verified (or the claim is rejected) when decoding.
    jwt_audience: str = Field(default="fastapi-users:auth", alias="JWT_AUDIENCE")

    # Invitations
    # Base URL of the user-facing frontend; the invite accept link is built as
    # f"{frontend_base_url}/invite/{token}". Must point at where the Next.js app
    # is served (http://localhost:3000 in dev).
    frontend_base_url: str = Field(default="http://localhost:3000", alias="FRONTEND_BASE_URL")
    # How long a pending invitation stays valid. 168h = 7 days.
    invite_token_ttl_hours: int = Field(default=168, alias="INVITE_TOKEN_TTL_HOURS")

    # Lead outbox drain (Phase 2) — a background task forwards undelivered
    # lead_outbox rows to admin_service's internal ingest endpoint. This is the
    # one isolated cross-service hop; it never blocks the invite request path and
    # survives admin_service being down (rows stay undelivered, retried later).
    admin_service_url: str = Field(default="http://admin_api:8000", alias="ADMIN_SERVICE_URL")
    admin_ingest_secret: str = Field(default="super-secret-ingest-key", alias="ADMIN_INGEST_SECRET")
    lead_drain_enabled: bool = Field(default=True, alias="LEAD_DRAIN_ENABLED")
    lead_drain_interval_seconds: int = Field(default=30, alias="LEAD_DRAIN_INTERVAL_SECONDS")
    lead_drain_batch_size: int = Field(default=100, alias="LEAD_DRAIN_BATCH_SIZE")

    # AI / LLM Configuration
    default_llm_provider: str = Field(default="local", alias="DEFAULT_LLM_PROVIDER")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    local_llm_url: str = Field(default="http://localhost:1234/v1", alias="LOCAL_LLM_URL")
    default_model_name: str = Field(default="gpt-4o-mini", alias="DEFAULT_MODEL_NAME")

    # Celery / Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")

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

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_allowed_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
