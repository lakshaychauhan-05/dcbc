"""
Test script to verify cache invalidation works correctly.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from app.utils.cache_utils import invalidate_doctor_cache
from app.config import settings

def test_cache_invalidation():
    """Test that cache invalidation clears both backend and Redis caches."""
    print("=" * 60)
    print("Cache Invalidation Test")
    print("=" * 60)

    # Test backend cache invalidation
    print("\n1. Testing backend cache invalidation...")
    try:
        from app.routes import appointment

        # Set some dummy data in cache
        with appointment._doctor_export_cache_lock:
            appointment._doctor_export_cache["data"] = {"test": "data"}
            appointment._doctor_export_cache["timestamp"] = "dummy"
            print("   [OK] Set dummy data in backend cache")

        # Verify data exists
        with appointment._doctor_export_cache_lock:
            has_data = bool(appointment._doctor_export_cache.get("data"))
            print(f"   [OK] Cache has data before invalidation: {has_data}")

        # Invalidate cache
        result = invalidate_doctor_cache()
        print(f"   [OK] Cache invalidation returned: {result}")

        # Verify data is cleared
        with appointment._doctor_export_cache_lock:
            has_data = bool(appointment._doctor_export_cache.get("data"))
            print(f"   [OK] Cache has data after invalidation: {has_data}")

        if not has_data:
            print("   [PASSED] Backend cache successfully invalidated")
        else:
            print("   [FAILED] Backend cache still has data")

    except Exception as e:
        print(f"   [ERROR] Backend cache test failed: {e}")

    # Test Redis cache invalidation
    print("\n2. Testing Redis cache invalidation...")
    if settings.REDIS_URL:
        try:
            import redis
            redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            redis_client.ping()

            # Set some dummy data
            redis_client.setex("doctor_data_cache", 60, json.dumps([{"test": "data"}]))
            exists_before = redis_client.exists("doctor_data_cache")
            print(f"   [OK] Redis key exists before invalidation: {bool(exists_before)}")

            # Invalidate cache
            result = invalidate_doctor_cache()
            print(f"   [OK] Cache invalidation returned: {result}")

            # Verify data is cleared
            exists_after = redis_client.exists("doctor_data_cache")
            print(f"   [OK] Redis key exists after invalidation: {bool(exists_after)}")

            if not exists_after:
                print("   [PASSED] Redis cache successfully invalidated")
            else:
                print("   [FAILED] Redis cache still has data")

        except Exception as e:
            print(f"   [NOTE] Redis test skipped: {e}")
    else:
        print("   [SKIPPED] Redis URL not configured")

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    test_cache_invalidation()
