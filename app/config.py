"""
Application configuration management.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str
    
    # Security
    SERVICE_API_KEY: str
    
    # Google Calendar
    GOOGLE_CALENDAR_CREDENTIALS_PATH: str
    GOOGLE_CALENDAR_DELEGATED_ADMIN_EMAIL: str
    
    # Webhook Configuration
    WEBHOOK_BASE_URL: str  # Public base URL for webhooks (e.g., https://yourdomain.com)
    GOOGLE_CALENDAR_WEBHOOK_SECRET: str  # Secret token for webhook verification
    
    # RAG Service
    RAG_SERVICE_URL: Optional[str] = None
    RAG_SERVICE_API_KEY: Optional[str] = None
    
    # Application
    APP_NAME: str = "Calendar Booking Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
