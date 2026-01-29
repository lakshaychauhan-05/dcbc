"""
FastAPI application for the Admin Portal.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from admin_portal.config import admin_settings
from admin_portal.routes import auth, management


def create_app() -> FastAPI:
    app = FastAPI(
        title="Admin Portal",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=admin_settings.cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/admin")
    app.include_router(management.router)

    @app.get("/admin/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
