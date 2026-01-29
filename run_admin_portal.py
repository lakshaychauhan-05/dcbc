#!/usr/bin/env python3
"""
Entry point for running the Admin Portal service.
"""
import uvicorn
from admin_portal.config import admin_settings


if __name__ == "__main__":
    uvicorn.run(
        "admin_portal.main:app",
        host="0.0.0.0",
        port=admin_settings.ADMIN_PORTAL_PORT,
        reload=admin_settings.ADMIN_PORTAL_DEBUG,
        log_level="debug" if admin_settings.ADMIN_PORTAL_DEBUG else "info",
    )
