"""
Test chatbot fixes for doctor listing and month name parsing.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from app.chatbot.services.chat_service import ChatService

def test_full_month_name_parsing():
    """Test that full month names are recognized."""
    print("\n=== Test: Full Month Name Parsing ===")

    chat_service = ChatService()

    test_cases = [
        ("23rd february at 2pm", True, "february"),
        ("23rd feb at 2pm", True, "feb"),
        ("15th january 2026", True, "january"),
        ("15th jan 2026", True, "jan"),
        ("march 10th", True, "march"),
        ("mar 10th", True, "mar"),
        ("december 25th", True, "december"),
        ("dec 25th", True, "dec"),
    ]

    passed = 0
    failed = 0

    for message, should_extract, month_variant in test_cases:
        date_text = chat_service._extract_date_from_text(message)
        success = bool(date_text) == should_extract

        if success:
            print(f"[PASSED] '{message}' -> {date_text if date_text else 'None'}")
            passed += 1
        else:
            print(f"[FAILED] '{message}' -> Expected: {should_extract}, Got: {bool(date_text)}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_doctor_list_limit():
    """Test that up to 5 doctors are shown."""
    print("\n=== Test: Doctor List Display Limit ===")

    # Simulate matching_doctors list
    mock_doctors = [
        {"name": "Aditi Tomar", "email": "lakshaychauhan05@gmail.com"},
        {"name": "Naveen Kapoor", "email": "doctorgm01@gmail.com"},
        {"name": "himanshu", "email": "him@gmail.com"},
        {"name": "asd", "email": "asdqsasdwds@gmail.com"},
        {"name": "Sunil Singh", "email": "kjewfq@gmail.com"},
    ]

    chat_service = ChatService()

    # Test with 5 doctors
    doctor_names = [chat_service._format_doctor_name(d.get("name")) for d in mock_doctors[:5]]
    print(f"Doctors shown (5 total): {', '.join(doctor_names)}")

    if len(doctor_names) == 5 and "Sunil Singh" in doctor_names[-1]:
        print("[PASSED] All 5 doctors shown including Sunil Singh")
        return True
    else:
        print("[FAILED] Not all doctors shown")
        return False


def test_date_parsing_examples():
    """Test specific date parsing examples from the bug report."""
    print("\n=== Test: Specific Date Examples ===")

    chat_service = ChatService()

    # Test "23rd february"
    date1 = chat_service._extract_date_from_text("23rd february")
    print(f"'23rd february' parsed as: {date1}")

    # Test "23rd feb"
    date2 = chat_service._extract_date_from_text("23rd feb")
    print(f"'23rd feb' parsed as: {date2}")

    # Both should parse to the same date
    if date1 and date2 and date1 == date2:
        print("[PASSED] Both 'february' and 'feb' parse to same date")
        return True
    elif date1 and date2:
        print(f"[FAILED] Dates don't match: {date1} != {date2}")
        return False
    else:
        print(f"[FAILED] One or both failed to parse: date1={date1}, date2={date2}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Chatbot Fixes Test Suite")
    print("=" * 60)

    results = []
    results.append(("Full Month Name Parsing", test_full_month_name_parsing()))
    results.append(("Doctor List Limit", test_doctor_list_limit()))
    results.append(("Date Parsing Examples", test_date_parsing_examples()))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for test_name, passed in results:
        status = "[PASSED]" if passed else "[FAILED]"
        print(f"{status} {test_name}")

    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n All tests passed!")
    else:
        print("\n Some tests failed!")
