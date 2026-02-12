"""
Admin Portal routes.
"""
from app.admin.routes.auth import router as auth_router
from app.admin.routes.management import router as management_router

__all__ = ["auth_router", "management_router"]
