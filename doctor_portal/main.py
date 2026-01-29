"""
FastAPI application for the Doctor Portal.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from doctor_portal.config import portal_settings
from doctor_portal.routes import auth, dashboard


def create_app() -> FastAPI:
    app = FastAPI(
        title="Doctor Portal",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=portal_settings.cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/portal")
    app.include_router(dashboard.router, prefix="/portal")

    @app.get("/portal/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
