"""
Application configuration management.
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str
    
    # Security
    SERVICE_API_KEY: str
    SERVICE_API_KEYS: Optional[str] = None  # Comma-separated list for rotation
    API_KEY_RATE_LIMIT_PER_MINUTE: int = 120
    API_KEY_RATE_LIMIT_BURST: int = 30
    
    # Google Calendar
    GOOGLE_CALENDAR_CREDENTIALS_PATH: str
    GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL: str
    
    # Webhook Configuration
    WEBHOOK_BASE_URL: str  # Public base URL for webhooks (e.g., https://yourdomain.com)
    GOOGLE_CALENDAR_WEBHOOK_SECRET: str  # Secret token for webhook verification
    
    # Local/degraded mode controls
    DISABLE_CALENDAR_WORKERS: bool = False  # Skip starting calendar sync/watch/reconcile
    ALLOW_START_WITHOUT_API_KEY: bool = False  # Only for local/dev; never enable in prod

    # RAG Service
    RAG_SERVICE_URL: Optional[str] = None
    RAG_SERVICE_API_KEY: Optional[str] = None

    # Redis (optional, shared env compatibility)
    REDIS_URL: Optional[str] = None

    # CORS
    CORS_ALLOW_ORIGINS: Optional[str] = None  # Comma-separated list
    
    # Application
    APP_NAME: str = "Calendar Booking Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Availability search constraints
    MAX_AVAILABILITY_DAYS: int = 30
    MAX_AVAILABILITY_RESULTS: int = 200
    MAX_LIST_LIMIT: int = 200

    # Doctor export caching
    DOCTOR_EXPORT_CACHE_TTL_SECONDS: int = 60

    # Calendar sync worker
    CALENDAR_SYNC_MAX_RETRIES: int = 5
    CALENDAR_SYNC_RETRY_BASE_SECONDS: int = 15
    CALENDAR_SYNC_POLL_INTERVAL_SECONDS: int = 5

    # Calendar reconcile worker (Google Calendar -> DB backfill)
    CALENDAR_RECONCILE_ENABLED: bool = True
    CALENDAR_RECONCILE_INTERVAL_SECONDS: int = 900
    CALENDAR_RECONCILE_BATCH_SIZE: int = 50
    CALENDAR_RECONCILE_REQUIRE_ACTIVE_WATCH: bool = True

    # Timezone
    DEFAULT_TIMEZONE: str = "UTC"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @field_validator("DATABASE_URL")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @field_validator("SERVICE_API_KEYS")
    @classmethod
    def normalize_api_keys(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return ",".join([item.strip() for item in value.split(",") if item.strip()])

    @field_validator("CORS_ALLOW_ORIGINS")
    @classmethod
    def normalize_cors_origins(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return ",".join([item.strip() for item in value.split(",") if item.strip()])


settings = Settings()
