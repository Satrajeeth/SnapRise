from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    #App Configuration

    app_name: str = Field(default="SnapRise OTP Service", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    #Database Configuration
    database_url: str = Field(...,alias="DATABASE_URL")
    sync_database_url: str = Field(..., alias="SYNC_DATABASE_URL")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")

    #REDIS Configuration
    redis_url: str = Field(..., alias="REDIS_URL")
    redis_timeout: int = Field(default=5, alias="REDIS_TIMEOUT")


    #OTP LOGIC CONFIGURATION
    otp_length: int = Field(default=6, alias="OTP_LENGTH")
    otp_expiry_seconds: int = Field(default=300, alias="OTP_EXPIRY_SECONDS")
    otp_retry_limit: int = Field(default=5, alias="MAX_OTP_RETRY")
    otp_retry_delay_seconds: int = Field(default=60, alias="OTP_COOLDOWN_SECONDS")

    #CELERY Configuration
    celery_broker_url: str = Field(..., alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(..., alias="CELERY_RESULT_BACKEND")

    #API Configuration
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    allowed_origins: List[str] = Field(default=['*'], alias="ALLOWED_ORIGINS")

    #MODEL Configuration

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    #Validators (Production Safety)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls,value:str)->str:
        allowed = {"development","staging","production"}

        if value not in allowed:
            raise ValueError(f"Invalid environment: {value}. Allowed values are: {allowed}")
        return value
    
    @field_validator("otp_length")
    @classmethod
    def validate_otp_length(clas, value: int)-> int:
        if value < 4 or value >8:
            raise ValueError("OTP length must be between 4 and 8")
        return value
    
    @field_validator("allowed_origins",mode="before")
    @classmethod
    def split_allowed_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",")]
        return value
    
    #Cached Settings Instance
@lru_cache
def get_settings() -> "Settings":
    return Settings()