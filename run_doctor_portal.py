#!/usr/bin/env python3
"""
Entry point for running the Doctor Portal service.
"""
import uvicorn
from doctor_portal.config import portal_settings


if __name__ == "__main__":
    uvicorn.run(
        "doctor_portal.main:app",
        host="0.0.0.0",
        port=portal_settings.DOCTOR_PORTAL_PORT,
        reload=portal_settings.DOCTOR_PORTAL_DEBUG,
        log_level="debug" if portal_settings.DOCTOR_PORTAL_DEBUG else "info",
    )
