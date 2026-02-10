"""
FastAPI application for the Doctor Portal.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from doctor_portal.config import portal_settings
from doctor_portal.routes import auth, dashboard

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    # Get CORS origins and log them at startup
    cors_origins = portal_settings.cors_origins()
    logger.info(f"Doctor Portal CORS origins: {cors_origins}")
    print(f"[Doctor Portal] CORS origins configured: {cors_origins}")

    app = FastAPI(
        title="Doctor Portal",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/portal")
    app.include_router(dashboard.router, prefix="/portal")

    @app.get("/")
    async def root():
        return {
            "service": "Doctor Portal API",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "api_base": "/portal",
            "cors_origins": cors_origins
        }

    @app.get("/portal/health")
    async def health():
        return {"status": "ok", "cors_origins": cors_origins}

    return app


app = create_app()
