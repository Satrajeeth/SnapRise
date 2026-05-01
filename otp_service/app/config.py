from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="SnapRise OTP Service", alias="APP_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")

    database_url: str = Field(..., alias="DATABASE_URL")
    sync_database_url: str = Field(..., alias="SYNC_DATABASE_URL")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")

    redis_url: str = Field(..., alias="REDIS_URL")
    redis_timeout: int = Field(default=5, alias="REDIS_TIMEOUT")

    celery_broker_url: str = Field(..., alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(..., alias="CELERY_RESULT_BACKEND")

    api_prefix: str = Field(default="/v1", alias="API_PREFIX")
    allowed_origins: List[str] = Field(default=["*"], alias="ALLOWED_ORIGINS")

    smtp_host: str = Field(default="smtp", alias="SMTP_HOST")
    smtp_port: int = Field(default=25, alias="SMTP_PORT")
    smtp_from_email: str = Field(default="no-reply@smtp.local", alias="SMTP_FROM_EMAIL")
    smtp_timeout_seconds: int = Field(default=10, alias="SMTP_TIMEOUT_SECONDS")
    smtp_provider_id: str = Field(default="smtp-default", alias="SMTP_PROVIDER_ID")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=False, alias="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(default=False, alias="SMTP_USE_SSL")
    smtp_fallback_enabled: bool = Field(default=False, alias="SMTP_FALLBACK_ENABLED")

    otp_code_length: int = Field(default=6, alias="OTP_CODE_LENGTH")
    otp_ttl_seconds: int = Field(default=600, alias="OTP_TTL_SECONDS")
    otp_max_attempts: int = Field(default=5, alias="OTP_MAX_ATTEMPTS")
    otp_backoff_seconds: List[int] = Field(
        default=[30, 60, 120, 240],
        alias="OTP_BACKOFF_SECONDS",
    )
    otp_resend_cooldown_seconds: int = Field(
        default=60,
        alias="OTP_RESEND_COOLDOWN_SECONDS",
    )
    otp_idempotency_ttl_seconds: int = Field(
        default=600,
        alias="OTP_IDEMPOTENCY_TTL_SECONDS",
    )
    otp_retry_delay_seconds: int = Field(default=300, alias="OTP_RETRY_DELAY_SECONDS")
    otp_retry_max_jobs: int = Field(default=8, alias="OTP_RETRY_MAX_JOBS")
    provider_circuit_failure_threshold: int = Field(
        default=3,
        alias="PROVIDER_CIRCUIT_FAILURE_THRESHOLD",
    )
    provider_circuit_open_seconds: int = Field(
        default=120,
        alias="PROVIDER_CIRCUIT_OPEN_SECONDS",
    )

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

    @field_validator("otp_code_length")
    @classmethod
    def validate_otp_code_length(cls, value: int) -> int:
        if value < 4 or value > 8:
            raise ValueError("OTP code length must be between 4 and 8")
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_allowed_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("otp_backoff_seconds", mode="before")
    @classmethod
    def split_backoff_seconds(cls, value):
        if isinstance(value, str):
            return [int(item.strip()) for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
