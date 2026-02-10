"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import doctor, patient, appointment, webhooks, clinic
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

logger = logging.getLogger(__name__)

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Calendar Appointment Service",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Request ID middleware
app.middleware("http")(request_id_middleware)

# CORS middleware
cors_origins = []
if settings.CORS_ALLOW_ORIGINS:
    cors_origins = [origin.strip() for origin in settings.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]
else:
    # Local-friendly defaults for all UIs (chatbot/admin/doctor)
    cors_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(clinic.router, prefix="/api/v1/clinics", tags=["Clinics"], dependencies=[Depends(rate_limiter)])
app.include_router(doctor.router, prefix="/api/v1/doctors", tags=["Doctors"], dependencies=[Depends(rate_limiter)])
app.include_router(patient.router, prefix="/api/v1/patients", tags=["Patients"], dependencies=[Depends(rate_limiter)])
app.include_router(appointment.router, prefix="/api/v1/appointments", tags=["Appointments"], dependencies=[Depends(rate_limiter)])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy"
    }


@app.get("/health")
async def health():
    """Detailed health check endpoint."""
    checks = {
        "database": "unknown",
        "calendar_credentials": "unknown",
        "calendar_sync_worker": "unknown",
        "calendar_watch_worker": "unknown",
        "calendar_reconcile_worker": "unknown"
    }

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = "healthy"
        finally:
            db.close()
    except Exception:
        checks["database"] = "unhealthy"

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

    allowed_statuses = {"healthy", "disabled"}
    overall = "healthy" if all(v in allowed_statuses for v in checks.values()) else "degraded"

    return {
        "status": overall,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "checks": checks
    }


@app.on_event("startup")
async def startup_event():
    """Start background services."""
    if not settings.SERVICE_API_KEY and not settings.SERVICE_API_KEYS:
        if settings.ALLOW_START_WITHOUT_API_KEY:
            logger.warning("Starting without SERVICE_API_KEY; protect this only for local/dev use")
        else:
            raise RuntimeError("SERVICE_API_KEY or SERVICE_API_KEYS must be configured")

    if settings.DISABLE_CALENDAR_WORKERS:
        logger.warning("Calendar workers disabled via DISABLE_CALENDAR_WORKERS; Google sync/watch/reconcile will NOT run")
    else:
        if not settings.GOOGLE_CALENDAR_CREDENTIALS_PATH or not os.path.exists(settings.GOOGLE_CALENDAR_CREDENTIALS_PATH):
            raise RuntimeError("GOOGLE_CALENDAR_CREDENTIALS_PATH must point to a valid credentials file")
        calendar_sync_queue.start()
        calendar_watch_service.start()
        calendar_reconcile_service.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background services."""
    calendar_sync_queue.stop()
    calendar_watch_service.stop()
    calendar_reconcile_service.stop()
