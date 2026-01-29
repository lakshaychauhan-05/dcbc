"""
Settings for the doctor portal service.
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List


class PortalSettings(BaseSettings):
    """Portal-specific configuration."""

    DOCTOR_PORTAL_PORT: int = 5000
    DOCTOR_PORTAL_JWT_SECRET: str
    DOCTOR_PORTAL_JWT_ALGORITHM: str = "HS256"
    DOCTOR_PORTAL_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DOCTOR_PORTAL_REFRESH_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days
    DOCTOR_PORTAL_CORS_ORIGINS: Optional[str] = None  # comma-separated list
    DOCTOR_PORTAL_DEBUG: bool = False
    DOCTOR_PORTAL_OAUTH_CLIENT_ID: Optional[str] = None
    DOCTOR_PORTAL_OAUTH_CLIENT_SECRET: Optional[str] = None
    DOCTOR_PORTAL_OAUTH_REDIRECT_URI: Optional[str] = None
    DOCTOR_PORTAL_FRONTEND_CALLBACK_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

    @field_validator("DOCTOR_PORTAL_CORS_ORIGINS")
    @classmethod
    def normalize_origins(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return ",".join([item.strip() for item in value.split(",") if item.strip()])

    def cors_origins(self) -> List[str]:
        if self.DOCTOR_PORTAL_CORS_ORIGINS:
            return [item.strip() for item in self.DOCTOR_PORTAL_CORS_ORIGINS.split(",") if item.strip()]
        # Sensible defaults for local dev (backend 5000, frontend 5173)
        return ["http://localhost:5000", "http://127.0.0.1:5000", "http://localhost:5173", "http://127.0.0.1:5173"]


portal_settings = PortalSettings()
