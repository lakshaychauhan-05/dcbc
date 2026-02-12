"""
Unified FastAPI application entry point.
Consolidates Core Calendar API, Doctor Portal, Admin Portal, and Chatbot services.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import doctor, patient, appointment, clinic
from app.security import rate_limiter
from fastapi import Depends
from app.logging_config import setup_logging
from app.services.calendar_sync_queue import calendar_sync_queue
from app.services.calendar_reconcile_service import calendar_reconcile_service
from app.services.calendar_watch_service import calendar_watch_service
from app.middleware.request_id import request_id_middleware
from app.database import SessionLocal
from sqlalchemy import text
import os
import logging

# Import portal, admin, and chatbot routers
from app.portal.routes.auth import router as portal_auth_router
from app.portal.routes.dashboard import router as portal_dashboard_router
from app.admin.routes.auth import router as admin_auth_router
from app.admin.routes.management import router as admin_management_router
from app.chatbot.routes.chat import router as chatbot_router

logger = logging.getLogger(__name__)

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Unified Calendar Booking Platform - Core API, Doctor Portal, Admin Portal, and Chatbot",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Request ID middleware
app.middleware("http")(request_id_middleware)

# CORS middleware - unified for all services
cors_origins = settings.get_cors_origins()
logger.info(f"CORS origins configured: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== CORE API ROUTES ==============
app.include_router(
    clinic.router,
    prefix="/api/v1/clinics",
    tags=["Clinics"],
    dependencies=[Depends(rate_limiter)]
)
app.include_router(
    doctor.router,
    prefix="/api/v1/doctors",
    tags=["Doctors"],
    dependencies=[Depends(rate_limiter)]
)
app.include_router(
    patient.router,
    prefix="/api/v1/patients",
    tags=["Patients"],
    dependencies=[Depends(rate_limiter)]
)
app.include_router(
    appointment.router,
    prefix="/api/v1/appointments",
    tags=["Appointments"],
    dependencies=[Depends(rate_limiter)]
)

# ============== DOCTOR PORTAL ROUTES ==============
app.include_router(
    portal_auth_router,
    prefix="/portal/auth",
    tags=["Portal Auth"]
)
app.include_router(
    portal_dashboard_router,
    prefix="/portal/dashboard",
    tags=["Portal Dashboard"]
)

# ============== ADMIN PORTAL ROUTES ==============
app.include_router(
    admin_auth_router,
    prefix="/admin",
    tags=["Admin Auth"]
)
app.include_router(
    admin_management_router,
    prefix="/admin",
    tags=["Admin Management"]
)

# ============== CHATBOT ROUTES ==============
app.include_router(
    chatbot_router,
    prefix="/chatbot/api/v1/chat",
    tags=["Chatbot"]
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
        "endpoints": {
            "core_api": "/api/v1",
            "portal": "/portal",
            "admin": "/admin",
            "chatbot": "/chatbot/api/v1",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health():
    """Detailed health check endpoint."""
    checks = {
        "database": "unknown",
        "calendar_credentials": "unknown",
        "calendar_sync_worker": "unknown",
        "calendar_watch_worker": "unknown",
        "calendar_reconcile_worker": "unknown",
        "openai": "unknown"
    }

    # Check database
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = "healthy"
        finally:
            db.close()
    except Exception:
        checks["database"] = "unhealthy"

    # Check calendar workers
    credentials_path = settings.GOOGLE_CALENDAR_CREDENTIALS_PATH
    if settings.DISABLE_CALENDAR_WORKERS:
        checks["calendar_credentials"] = "disabled"
        checks["calendar_sync_worker"] = "disabled"
        checks["calendar_watch_worker"] = "disabled"
        checks["calendar_reconcile_worker"] = "disabled"
    else:
        checks["calendar_credentials"] = "healthy" if credentials_path and os.path.exists(credentials_path) else "missing"
        checks["calendar_sync_worker"] = "healthy" if calendar_sync_queue.is_running() else "stopped"
        checks["calendar_watch_worker"] = "healthy" if calendar_watch_service.is_running() else "stopped"
        checks["calendar_reconcile_worker"] = "healthy" if calendar_reconcile_service.is_running() else "stopped"

    # Check OpenAI
    checks["openai"] = "configured" if settings.OPENAI_API_KEY else "not_configured"

    allowed_statuses = {"healthy", "disabled", "configured"}
    overall = "healthy" if all(v in allowed_statuses for v in checks.values()) else "degraded"

    return {
        "status": overall,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "checks": checks
    }


# Portal-specific health endpoint for backwards compatibility
@app.get("/portal/health")
async def portal_health():
    return {"status": "ok", "service": "Doctor Portal"}


# Admin-specific health endpoint for backwards compatibility
@app.get("/admin/health")
async def admin_health():
    return {"status": "ok", "service": "Admin Portal"}


# Chatbot-specific health endpoint for backwards compatibility
@app.get("/chatbot/api/v1/health")
async def chatbot_health():
    return {
        "status": "ok" if settings.OPENAI_API_KEY else "degraded",
        "service": "Chatbot",
        "openai_configured": bool(settings.OPENAI_API_KEY)
    }


@app.on_event("startup")
async def startup_event():
    """Start background services."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Running on port {settings.PORT}")

    # Validate API key
    if not settings.SERVICE_API_KEY and not settings.SERVICE_API_KEYS:
        if settings.ALLOW_START_WITHOUT_API_KEY:
            logger.warning("Starting without SERVICE_API_KEY; protect this only for local/dev use")
        else:
            raise RuntimeError("SERVICE_API_KEY or SERVICE_API_KEYS must be configured")

    # Start calendar workers if enabled
    if settings.DISABLE_CALENDAR_WORKERS:
        logger.warning("Calendar workers disabled via DISABLE_CALENDAR_WORKERS; Google sync/watch/reconcile will NOT run")
    else:
        if not settings.GOOGLE_CALENDAR_CREDENTIALS_PATH or not os.path.exists(settings.GOOGLE_CALENDAR_CREDENTIALS_PATH):
            raise RuntimeError("GOOGLE_CALENDAR_CREDENTIALS_PATH must point to a valid credentials file")
        calendar_sync_queue.start()
        calendar_watch_service.start()
        calendar_reconcile_service.start()

    # Log OpenAI status
    if settings.OPENAI_API_KEY:
        logger.info("OpenAI API key configured - chatbot enabled")
    else:
        logger.warning("OpenAI API key not configured - chatbot will not work")

    logger.info(f"CORS origins: {settings.get_cors_origins()}")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background services."""
    logger.info(f"Shutting down {settings.APP_NAME}")
    calendar_sync_queue.stop()
    calendar_watch_service.stop()
    calendar_reconcile_service.stop()
