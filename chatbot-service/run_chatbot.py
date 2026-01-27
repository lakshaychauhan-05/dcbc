#!/usr/bin/env python3
"""
Simple script to run the Chatbot Service FastAPI application.
"""
import os
import socket
import uvicorn
from app.core.config import settings


def _port_available(port: int, host: str = "0.0.0.0") -> bool:
    """Check if a port is available for binding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def _select_port() -> int:
    """Pick a usable port, preferring CHATBOT_PORT or settings.PORT."""
    preferred_port = int(os.getenv("CHATBOT_PORT", settings.PORT))
    if preferred_port == 8001:
        preferred_port = 8002

    fallback_ports = [preferred_port, 8002, 8001, 8003, 8004]
    for port in fallback_ports:
        if _port_available(port, settings.HOST):
            return port
    return preferred_port


if __name__ == "__main__":
    port = _select_port()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=port,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )