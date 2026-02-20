"""
Cache utilities for invalidating doctor data caches.
"""
import logging
import redis
import threading
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Import the backend cache from appointment routes
# This is a module-level variable, so we need to access it directly
_backend_cache_invalidated = False


def invalidate_doctor_cache():
    """
    Invalidate all doctor data caches.

    This clears:
    1. Backend in-memory cache (_doctor_export_cache in appointment routes)
    2. Chatbot Redis cache (doctor_data_cache)

    Should be called whenever doctor data changes (create, update, delete).
    """
    try:
        # Invalidate backend in-memory cache
        # Import here to avoid circular dependency
        from app.routes import appointment

        if hasattr(appointment, '_doctor_export_cache_lock') and hasattr(appointment, '_doctor_export_cache'):
            with appointment._doctor_export_cache_lock:
                appointment._doctor_export_cache.clear()
                logger.info("Backend doctor cache invalidated")

        # Invalidate Redis cache if available
        if settings.REDIS_URL:
            try:
                redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
                redis_client.ping()
                deleted = redis_client.delete("doctor_data_cache")
                if deleted:
                    logger.info("Redis doctor cache invalidated")
                else:
                    logger.debug("Redis doctor cache key did not exist")
            except Exception as e:
                logger.warning(f"Failed to invalidate Redis cache: {e}")

        return True

    except Exception as e:
        logger.error(f"Error invalidating doctor cache: {e}")
        return False
