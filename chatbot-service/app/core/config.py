"""
Configuration settings for the Chatbot Service.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "AI Appointment Chatbot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8002

    # OpenAI / LLM
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"  # or "gpt-3.5-turbo"
    OPENAI_TEMPERATURE: float = 0.3
    OPENAI_MAX_TOKENS: int = 1000

    # Calendar Service
    CALENDAR_SERVICE_URL: str = "http://localhost:8000"
    CALENDAR_SERVICE_API_KEY: str = "dev-api-key"

    # Redis (optional, for conversation state)
    REDIS_URL: Optional[str] = None

    # CORS
    CORS_ALLOW_ORIGINS: Optional[str] = None

    # Rate limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 120
    RATE_LIMIT_BURST: int = 30

    # WebSocket
    WEBSOCKET_PING_INTERVAL: int = 30
    WEBSOCKET_PING_TIMEOUT: int = 10

    # Conversation settings
    MAX_CONVERSATION_TURNS: int = 10
    MAX_CONVERSATION_HISTORY: int = 50  # Fallback if turns not set
    CONVERSATION_TIMEOUT_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()