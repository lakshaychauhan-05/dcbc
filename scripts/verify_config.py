"""
Configuration Verification Script
Verifies all service configurations are correct for end-to-end operation.
"""
import os
import sys
import httpx
from pathlib import Path

def check_calendar_service():
    """Check if calendar service is running and accessible."""
    print("\n=== Calendar Service Check ===")
    
    # Check if .env exists
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found in root directory")
        print("   Please create .env file from env.example")
        return False
    
    # Try to read SERVICE_API_KEY (if possible)
    try:
        with open(env_path, 'r') as f:
            content = f.read()
            if 'SERVICE_API_KEY' in content:
                print("✅ .env file contains SERVICE_API_KEY")
            else:
                print("⚠️  SERVICE_API_KEY not found in .env")
    except Exception as e:
        print(f"⚠️  Could not read .env file: {e}")
    
    # Check if service is running on port 8000
    try:
        response = httpx.get("http://localhost:8000/health", timeout=5.0)
        if response.status_code == 200:
            print("✅ Calendar service is running on port 8000")
            return True
        else:
            print(f"⚠️  Calendar service responded with status {response.status_code}")
    except httpx.ConnectError:
        print("❌ Calendar service is not running on port 8000")
        print("   Start it with: python run.py")
        return False
    except Exception as e:
        print(f"❌ Error checking calendar service: {e}")
        return False
    
    return False

def check_chatbot_service():
    """Check if chatbot service is running and accessible."""
    print("\n=== Chatbot Service Check ===")
    
    # Check chatbot-service .env
    chatbot_env = Path("chatbot-service/.env")
    if not chatbot_env.exists():
        print("⚠️  chatbot-service/.env not found")
        print("   Create it from chatbot-service/env.example")
    else:
        print("✅ chatbot-service/.env exists")
    
    # Check if service is running on port 8001
    try:
        response = httpx.get("http://localhost:8001/api/v1/health/", timeout=5.0)
        if response.status_code == 200:
            print("✅ Chatbot service is running on port 8001")
            return True
        else:
            print(f"⚠️  Chatbot service responded with status {response.status_code}")
    except httpx.ConnectError:
        print("❌ Chatbot service is not running on port 8001")
        print("   Start it with: cd chatbot-service && python run_chatbot.py")
        return False
    except Exception as e:
        print(f"❌ Error checking chatbot service: {e}")
        return False
    
    return False

def check_api_connection():
    """Check if chatbot can connect to calendar service."""
    print("\n=== API Connection Check ===")
    
    # This would require the API key from .env
    # For now, just check if both services are running
    calendar_running = False
    chatbot_running = False
    
    try:
        response = httpx.get("http://localhost:8000/health", timeout=5.0)
        calendar_running = response.status_code == 200
    except:
        pass
    
    try:
        response = httpx.get("http://localhost:8001/api/v1/health/", timeout=5.0)
        chatbot_running = response.status_code == 200
    except:
        pass
    
    if calendar_running and chatbot_running:
        print("✅ Both services are running")
        print("⚠️  To test API connection, ensure:")
        print("   1. Calendar service .env has: SERVICE_API_KEY=dev-api-key")
        print("   2. Chatbot service .env has: CALENDAR_SERVICE_API_KEY=dev-api-key")
        print("   3. Chatbot service .env has: CALENDAR_SERVICE_URL=http://localhost:8000")
        return True
    else:
        print("❌ One or both services are not running")
        return False

def main():
    """Run all configuration checks."""
    print("=" * 50)
    print("Configuration Verification")
    print("=" * 50)
    
    results = []
    results.append(check_calendar_service())
    results.append(check_chatbot_service())
    results.append(check_api_connection())
    
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    
    if all(results):
        print("✅ All checks passed!")
    else:
        print("⚠️  Some checks failed. Please review the issues above.")
        print("\nRequired Configuration:")
        print("\n1. Root .env file should have:")
        print("   SERVICE_API_KEY=dev-api-key")
        print("   (and other required variables)")
        print("\n2. chatbot-service/.env should have:")
        print("   CALENDAR_SERVICE_URL=http://localhost:8000")
        print("   CALENDAR_SERVICE_API_KEY=dev-api-key")
        print("   OPENAI_API_KEY=your_openai_key")
    
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())