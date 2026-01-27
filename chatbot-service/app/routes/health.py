"""
Health check routes for the Chatbot Service.
"""
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": settings.APP_NAME}


@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check with component status."""
    health_status = {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "components": {
            "openai_api": "available" if settings.OPENAI_API_KEY else "not_configured",
            "calendar_service": "configured" if settings.CALENDAR_SERVICE_URL else "not_configured"
        }
    }

    # Check if all components are healthy
    components_healthy = all(
        status in ["available", "configured"]
        for status in health_status["components"].values()
    )

    if not components_healthy:
        health_status["status"] = "degraded"

    return health_status