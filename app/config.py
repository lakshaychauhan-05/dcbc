"""
Unified application configuration management.
Consolidates settings from all services: Core API, Doctor Portal, Admin Portal, and Chatbot.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional, List

# Get the project root directory (where .env is located)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


class Settings(BaseSettings):
    """Unified application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # ===========================================
    # DATABASE
    # ===========================================
    DATABASE_URL: str

    # ===========================================
    # CORE API SECURITY
    # ===========================================
    SERVICE_API_KEY: str = ""
    SERVICE_API_KEYS: Optional[str] = None  # Comma-separated list for rotation
    API_KEY_RATE_LIMIT_PER_MINUTE: int = 120
    API_KEY_RATE_LIMIT_BURST: int = 30
    ALLOW_START_WITHOUT_API_KEY: bool = False  # Only for local/dev; never enable in prod

    # ===========================================
    # GOOGLE CALENDAR (can be disabled)
    # ===========================================
    GOOGLE_CALENDAR_CREDENTIALS_PATH: str = ""
    GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL: str = ""
    WEBHOOK_BASE_URL: str = ""  # Public base URL for webhooks
    GOOGLE_CALENDAR_WEBHOOK_SECRET: str = ""  # Secret token for webhook verification
    DISABLE_CALENDAR_WORKERS: bool = True  # Disabled by default for unified setup

    # ===========================================
    # DOCTOR PORTAL AUTHENTICATION
    # ===========================================
    DOCTOR_PORTAL_JWT_SECRET: str
    DOCTOR_PORTAL_JWT_ALGORITHM: str = "HS256"
    DOCTOR_PORTAL_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DOCTOR_PORTAL_REFRESH_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days

    # Google OAuth for Doctor Login
    DOCTOR_PORTAL_OAUTH_CLIENT_ID: Optional[str] = None
    DOCTOR_PORTAL_OAUTH_CLIENT_SECRET: Optional[str] = None
    DOCTOR_PORTAL_OAUTH_REDIRECT_URI: Optional[str] = None
    DOCTOR_PORTAL_FRONTEND_CALLBACK_URL: Optional[str] = None

    # ===========================================
    # ADMIN PORTAL AUTHENTICATION
    # ===========================================
    ADMIN_PORTAL_JWT_SECRET: str
    ADMIN_PORTAL_JWT_ALGORITHM: str = "HS256"
    ADMIN_PORTAL_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ADMIN_EMAIL: str
    ADMIN_PASSWORD_HASH: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None  # convenience for local dev; hash preferred

    # ===========================================
    # CHATBOT / OPENAI
    # ===========================================
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TEMPERATURE: float = 0.3
    OPENAI_MAX_TOKENS: int = 1000
    MAX_CONVERSATION_TURNS: int = 10
    MAX_CONVERSATION_HISTORY: int = 50
    CONVERSATION_TIMEOUT_MINUTES: int = 30

    # ===========================================
    # REDIS (Optional - for chatbot conversation state)
    # ===========================================
    REDIS_URL: Optional[str] = None

    # ===========================================
    # RAG SERVICE (Optional)
    # ===========================================
    RAG_SERVICE_URL: Optional[str] = None
    RAG_SERVICE_API_KEY: Optional[str] = None

    # ===========================================
    # CORS
    # ===========================================
    CORS_ALLOW_ORIGINS: Optional[str] = None  # Comma-separated list

    # ===========================================
    # APPLICATION
    # ===========================================
    APP_NAME: str = "Calendar Booking Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    PORT: int = 8000
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    # ===========================================
    # AVAILABILITY SEARCH CONSTRAINTS
    # ===========================================
    MAX_AVAILABILITY_DAYS: int = 30
    MAX_AVAILABILITY_RESULTS: int = 200
    MAX_LIST_LIMIT: int = 200

    # ===========================================
    # DOCTOR EXPORT CACHING
    # ===========================================
    DOCTOR_EXPORT_CACHE_TTL_SECONDS: int = 60

    # ===========================================
    # CALENDAR SYNC WORKER (when enabled)
    # ===========================================
    CALENDAR_SYNC_MAX_RETRIES: int = 5
    CALENDAR_SYNC_RETRY_BASE_SECONDS: int = 15
    CALENDAR_SYNC_POLL_INTERVAL_SECONDS: int = 5

    # ===========================================
    # CALENDAR RECONCILE WORKER (when enabled)
    # ===========================================
    CALENDAR_RECONCILE_ENABLED: bool = True
    CALENDAR_RECONCILE_INTERVAL_SECONDS: int = 900
    CALENDAR_RECONCILE_BATCH_SIZE: int = 50
    CALENDAR_RECONCILE_REQUIRE_ACTIVE_WATCH: bool = True

    # ===========================================
    # SMS NOTIFICATIONS (Twilio)
    # ===========================================
    SMS_NOTIFICATIONS_ENABLED: bool = False
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # Twilio Content Template IDs (for DLT compliance in India)
    TWILIO_TEMPLATE_DOCTOR_BOOKING: Optional[str] = None
    TWILIO_TEMPLATE_DOCTOR_RESCHEDULE: Optional[str] = None
    TWILIO_TEMPLATE_DOCTOR_CANCEL: Optional[str] = None
    TWILIO_TEMPLATE_PATIENT_BOOKING: Optional[str] = None
    TWILIO_TEMPLATE_PATIENT_RESCHEDULE: Optional[str] = None
    TWILIO_TEMPLATE_PATIENT_CANCEL: Optional[str] = None

    # ===========================================
    # CLINIC INFO (used in notifications)
    # ===========================================
    CLINIC_NAME: str = "Medical Clinic"
    CLINIC_ADDRESS: Optional[str] = None

    # ===========================================
    # VALIDATORS
    # ===========================================
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

    @field_validator("GOOGLE_CALENDAR_CREDENTIALS_PATH")
    @classmethod
    def normalize_credentials_path(cls, value: str) -> str:
        """Convert relative path to absolute path based on project root."""
        if not value:
            return value
        if os.path.isabs(value):
            return value
        if value.startswith("./"):
            value = value[2:]
        abs_path = str(PROJECT_ROOT / value)
        return abs_path

    # ===========================================
    # HELPER METHODS
    # ===========================================
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as a list."""
        if self.CORS_ALLOW_ORIGINS:
            return [item.strip() for item in self.CORS_ALLOW_ORIGINS.split(",") if item.strip()]
        # Default: unified frontend on port 5173
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    def get_api_keys(self) -> List[str]:
        """Get all valid API keys as a list."""
        keys = []
        if self.SERVICE_API_KEY:
            keys.append(self.SERVICE_API_KEY)
        if self.SERVICE_API_KEYS:
            keys.extend([k.strip() for k in self.SERVICE_API_KEYS.split(",") if k.strip()])
        return list(set(keys))


settings = Settings()
