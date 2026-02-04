#!/usr/bin/env python3
"""
Integration test script to verify end-to-end functionality.
Tests the complete flow from chatbot to calendar booking.
"""
import asyncio
import httpx
import json
import time
import os
from datetime import datetime, date, time as dt_time

# Configuration
CALENDAR_SERVICE_URL = "http://localhost:8000"
CHATBOT_SERVICE_URL = "http://localhost:8001"
CALENDAR_API_KEY = os.getenv("SERVICE_API_KEY", "dev-api-key")

async def test_calendar_service():
    """Test calendar service endpoints."""
    print("Testing Calendar Service...")

    async with httpx.AsyncClient(headers={"X-API-Key": CALENDAR_API_KEY}) as client:
        try:
            # Test health check
            response = await client.get(f"{CALENDAR_SERVICE_URL}/health")
            assert response.status_code == 200
            print("✓ Calendar service health check passed")

            # Test doctor export
            response = await client.get(f"{CALENDAR_SERVICE_URL}/api/v1/doctors/export")
            assert response.status_code == 200
            doctor_data = response.json()
            assert "doctors" in doctor_data
            assert len(doctor_data["doctors"]) > 0
            print(f"✓ Doctor export working - found {len(doctor_data['doctors'])} doctors")

            # Test availability search
            response = await client.get(
                f"{CALENDAR_SERVICE_URL}/api/v1/appointments/availability/search",
                params={"specialization": "Cardiology"}
            )
            assert response.status_code == 200
            availability_data = response.json()
            print(f"✓ Availability search working - found {availability_data['total_results']} results")

            return doctor_data

        except Exception as e:
            print(f"✗ Calendar service test failed: {e}")
            return None

async def test_chatbot_service():
    """Test chatbot service endpoints."""
    print("\nTesting Chatbot Service...")

    async with httpx.AsyncClient(headers={"X-API-Key": CALENDAR_API_KEY}) as client:
        try:
            # Test health check
            response = await client.get(f"{CHATBOT_SERVICE_URL}/api/v1/health/")
            assert response.status_code == 200
            print("✓ Chatbot service health check passed")

            # Test chat endpoint
            chat_request = {
                "message": "Hello, I want to book an appointment",
                "user_id": "test_user"
            }

            response = await client.post(
                f"{CHATBOT_SERVICE_URL}/api/v1/chat/",
                json=chat_request,
                timeout=30.0
            )
            assert response.status_code == 200
            chat_response = response.json()
            assert "conversation_id" in chat_response
            assert "message" in chat_response
            print("✓ Chat endpoint working")

            conversation_id = chat_response["conversation_id"]

            # Test conversation history
            response = await client.get(f"{CHATBOT_SERVICE_URL}/api/v1/chat/conversation/{conversation_id}")
            assert response.status_code == 200
            history = response.json()
            assert len(history["messages"]) > 0
            print("✓ Conversation history working")

            return conversation_id

        except Exception as e:
            print(f"✗ Chatbot service test failed: {e}")
            return None

async def test_end_to_end_flow():
    """Test complete end-to-end booking flow."""
    print("\nTesting End-to-End Flow...")

    async with httpx.AsyncClient() as client:
        try:
            # Step 1: Get doctor information
            response = await client.get(f"{CALENDAR_SERVICE_URL}/api/v1/doctors/export")
            doctors = response.json()["doctors"]
            test_doctor = doctors[0]  # Use first doctor

            # Step 2: Start conversation
            chat_request = {
                "message": f"I want to book an appointment with {test_doctor['specialization']} specialist",
                "user_id": "e2e_test_user"
            }

            response = await client.post(f"{CHATBOT_SERVICE_URL}/api/v1/chat/", json=chat_request)
            chat_response = response.json()
            conversation_id = chat_response["conversation_id"]

            # Step 3: Provide booking details
            booking_message = f"My name is Test User, phone is 123-456-7890, I need to see a {test_doctor['specialization']}"
            chat_request = {
                "message": booking_message,
                "conversation_id": conversation_id
            }

            response = await client.post(f"{CHATBOT_SERVICE_URL}/api/v1/chat/", json=chat_request)
            assert response.status_code == 200

            # Step 4: Confirm booking (this would normally require more interaction)
            confirm_message = "Yes, please book it for tomorrow at 10 AM"
            chat_request = {
                "message": confirm_message,
                "conversation_id": conversation_id
            }

            response = await client.post(f"{CHATBOT_SERVICE_URL}/api/v1/chat/", json=chat_request)
            chat_response = response.json()

            print("✓ End-to-end flow completed successfully")
            print(f"  Conversation ID: {conversation_id}")
            print(f"  Final response: {chat_response['message'][:100]}...")

            return True

        except Exception as e:
            print(f"✗ End-to-end flow test failed: {e}")
            return False

async def main():
    """Run all integration tests."""
    print("Starting Integration Tests...")
    print("=" * 50)

    # Wait for services to be ready
    print("Waiting for services to be ready...")
    await asyncio.sleep(5)

    results = []

    # Test individual services
    calendar_result = await test_calendar_service()
    chatbot_result = await test_chatbot_service()

    results.extend([calendar_result is not None, chatbot_result is not None])

    # Test end-to-end flow if both services are working
    if all(results):
        e2e_result = await test_end_to_end_flow()
        results.append(e2e_result)
    else:
        print("\nSkipping end-to-end test due to service failures")
        results.append(False)

    # Summary
    print("\n" + "=" * 50)
    print("Integration Test Results:")
    print(f"Calendar Service: {'PASS' if results[0] else 'FAIL'}")
    print(f"Chatbot Service: {'PASS' if results[1] else 'FAIL'}")
    print(f"End-to-End Flow: {'PASS' if results[2] else 'FAIL'}")

    success_count = sum(results)
    total_count = len(results)

    print(f"\nOverall: {success_count}/{total_count} tests passed")

    if success_count == total_count:
        print("🎉 All integration tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())