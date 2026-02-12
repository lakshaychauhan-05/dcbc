"""
Doctor Portal routes.
"""
from app.portal.routes.auth import router as auth_router
from app.portal.routes.dashboard import router as dashboard_router

__all__ = ["auth_router", "dashboard_router"]
