"""
Main Chat Service that orchestrates LLM, calendar client, and conversation management.
All times are in IST (Asia/Kolkata).
"""
import logging
import re
import traceback
import json
import hashlib
from difflib import get_close_matches
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date, timedelta, time as dt_time
from dateutil import parser as date_parser
from zoneinfo import ZoneInfo

# IST timezone
IST = ZoneInfo("Asia/Kolkata")

import redis

from app.config import settings
from app.chatbot.models.chat import (
    ChatRequest,
    ChatResponse,
    IntentType,
    ConversationState,
    MessageRole,
    BookingDetails,
    EntityType,
    IntentClassification
)
from app.chatbot.services.llm_service import LLMService
from app.chatbot.services.calendar_client import CalendarClient
from app.chatbot.services.conversation_manager import ConversationManager

logger = logging.getLogger(__name__)


class ChatService:
    """Main service for handling chat interactions."""

    BOOKING_CONTEXT_FIELDS = (
        "appointment_id",
        "selected_doctor_email",
        "doctor_email",
        "doctor_name",
        "specialization",
        "date",
        "time",
        "patient_name",
        "patient_phone",
        "patient_email",
        "symptoms",
        "appointment_type",
        "reschedule_date",
        "reschedule_time"
    )

    def __init__(self):
        self.llm_service = LLMService()
        self.conversation_manager = ConversationManager()
        self._redis = None
        if settings.REDIS_URL:
            try:
                self._redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
                self._redis.ping()
            except Exception as e:
                logger.warning(f"Redis unavailable, caching disabled: {e}")
                self._redis = None
        self._doctor_cache_key = "doctor_data_cache"
        self._doctor_cache_ttl_seconds = 300

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """Process a user message and generate a response."""
        try:
            # Get or create conversation
            conversation_id = request.conversation_id
            conversation = None
            if conversation_id:
                conversation = self.conversation_manager.get_conversation(conversation_id)

            if not conversation_id or conversation is None:
                conversation = self.conversation_manager.create_conversation(request.user_id)
                conversation_id = conversation.id

            # Get conversation history
            conversation_history = self.conversation_manager.get_conversation_history(conversation_id)

            # Add user message to conversation
            self.conversation_manager.add_message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=request.message,
                metadata=request.metadata
            )

            # Handle pending confirmation before intent classification
            pending_action = conversation.context.get("pending_action") if conversation else None
            if pending_action and self._is_affirmative(request.message):
                response_text = await self._execute_pending_action(conversation_id)
                self.conversation_manager.add_message(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=response_text
                )
                return ChatResponse(
                    conversation_id=conversation_id,
                    message=response_text,
                    intent=None,
                    suggested_actions=[],
                    requires_confirmation=False,
                    booking_details=None
                )
            elif pending_action and self._is_negative(request.message):
                # Get booking context to offer helpful alternatives
                booking_context = self.conversation_manager.get_booking_context(conversation_id)
                self.conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    state=ConversationState.INITIAL,
                    context={
                        "pending_action": None,
                        "reschedule_in_progress": False,
                        "reschedule_date": None,
                        "reschedule_time": None
                    }
                )

                # Generate helpful response based on what was being cancelled
                if pending_action == "book":
                    response_text = self._generate_cancellation_alternatives(booking_context)
                elif pending_action == "reschedule":
                    response_text = "No problem, I've cancelled the reschedule request. Would you like to try a different date or time?"
                elif pending_action == "cancel":
                    response_text = "Okay, I won't cancel the appointment. Is there anything else I can help you with?"
                else:
                    response_text = "Understood, I won't proceed with that. How else can I assist you?"

                self.conversation_manager.add_message(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=response_text
                )
                return ChatResponse(
                    conversation_id=conversation_id,
                    message=response_text,
                    intent=None,
                    suggested_actions=["book_appointment", "get_doctor_info", "check_availability"],
                    requires_confirmation=False,
                    booking_details=None
                )
            elif pending_action and self._is_clarifying_question(request.message):
                # User is asking a clarifying question about the booking, not confirming
                # Clear pending action and allow them to get more information
                logger.info("Detected clarifying question during confirmation, allowing user to continue")
                self.conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    state=ConversationState.GATHERING_INFO,
                    context={"pending_action": None}
                )
                # Continue to intent classification for the question

            # Classify intent and extract entities
            intent_classification = await self.llm_service.classify_intent(
                request.message,
                conversation_history
            )
            # Fallback to rule-based intent detection when LLM is uncertain
            intent_classification = self._apply_rule_based_intent(
                request.message,
                intent_classification
            )

            # Guard: keep user inside booking flow until completed
            # But allow breaking out for certain queries
            if conversation and conversation.state in [
                ConversationState.GATHERING_INFO,
                ConversationState.CONFIRMING_BOOKING,
                ConversationState.BOOKING_APPOINTMENT
            ]:
                message_lower = request.message.lower()

                # Check if user wants to break out of booking flow
                break_out_phrases = [
                    "tell me about", "about clinic", "about your clinic", "clinic info",
                    "doctor info", "who are", "list doctor", "which doctor", "all doctor",
                    "specialization", "what specialt", "help", "start over", "cancel booking",
                    "never mind", "forget it", "different doctor"
                ]
                wants_to_break_out = any(phrase in message_lower for phrase in break_out_phrases)

                # Check if user is asking for availability/slots/timings
                availability_keywords = ["timing", "slot", "available", "availability", "when", "other time", "more time"]
                is_asking_availability = any(kw in message_lower for kw in availability_keywords)

                # Check if user explicitly mentions a DIFFERENT doctor than current context
                explicit_new_doctor = self._match_doctor_name_in_message(request.message, await self._get_doctor_data())
                current_doctor = conversation.context.get("doctor_name") or conversation.context.get("last_doctor_name")
                is_changing_doctor = (
                    explicit_new_doctor and current_doctor and
                    not self._names_match(explicit_new_doctor, current_doctor)
                )

                if wants_to_break_out:
                    # User wants general info, break out of booking flow
                    logger.info("User wants to break out of booking flow")
                    self.conversation_manager.update_conversation(
                        conversation_id=conversation_id,
                        state=ConversationState.INITIAL,
                        context={"pending_action": None}
                    )
                    intent_classification.intent = IntentType.GET_DOCTOR_INFO
                elif is_changing_doctor:
                    # User explicitly wants a different doctor - clear old context and continue booking
                    logger.info(f"User changing doctor from '{current_doctor}' to '{explicit_new_doctor}'")
                    self.conversation_manager.update_conversation(
                        conversation_id=conversation_id,
                        context={
                            "doctor_name": explicit_new_doctor,
                            "last_doctor_name": explicit_new_doctor,
                            "doctor_email": None,
                            "last_doctor_email": None,
                            "selected_doctor_email": None
                        }
                    )
                elif intent_classification.intent not in [
                    IntentType.CANCEL_APPOINTMENT,
                    IntentType.RESCHEDULE_APPOINTMENT,
                    IntentType.CHECK_AVAILABILITY
                ] and not is_asking_availability:
                    logger.info(
                        "Forcing booking intent due to active booking state",
                        extra={"conversation_id": conversation_id}
                    )
                    intent_classification.intent = IntentType.BOOK_APPOINTMENT
                elif is_asking_availability:
                    # User wants to check other slots, switch to availability intent
                    intent_classification.intent = IntentType.CHECK_AVAILABILITY
                    # Reset booking confirmation state
                    self.conversation_manager.update_conversation(
                        conversation_id=conversation_id,
                        state=ConversationState.INITIAL,
                        context={"pending_action": None}
                    )

            # Auto-transition from availability -> booking when time is provided
            if conversation:
                availability_date = conversation.context.get("availability_date")
                last_doctor_name = conversation.context.get("last_doctor_name")
                availability_specialization = conversation.context.get("availability_specialization")
                if availability_date and self._extract_time_from_text(request.message):
                    if last_doctor_name or availability_specialization:
                        logger.info(
                            "Auto-transitioning to booking from availability",
                            extra={"conversation_id": conversation_id}
                        )
                        intent_classification.intent = IntentType.BOOK_APPOINTMENT

            # Get doctor data only when needed (including when symptoms are mentioned)
            doctor_data: List[Dict[str, Any]] = []
            if self._needs_doctor_data(intent_classification.intent, request.message):
                doctor_data = await self._get_doctor_data()

            # Generate response based on intent
            try:
                response_text = await self._generate_response_based_on_intent(
                    request.message,
                    intent_classification,
                    conversation_id,
                    doctor_data,
                    conversation_history
                )
            except Exception as e:
                logger.exception(f"Error generating response: {e}")
                response_text = "I'm sorry, I ran into an issue while responding. Please try again."

            # Safety: prevent LLM responses from claiming a booking without an API call
            if intent_classification.intent not in [
                IntentType.BOOK_APPOINTMENT,
                IntentType.RESCHEDULE_APPOINTMENT,
                IntentType.CANCEL_APPOINTMENT
            ]:
                if "booked" in response_text.lower():
                    response_text = (
                        "I can help you book an appointment. "
                        "Please share the doctor, date, and time you'd like."
                    )

            # Update conversation state
            new_state = self._determine_conversation_state(intent_classification.intent, conversation_id)
            self.conversation_manager.update_conversation(
                conversation_id=conversation_id,
                state=new_state
            )

            # Add assistant response to conversation
            self.conversation_manager.add_message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=response_text
            )

            # Determine suggested actions
            suggested_actions = self._get_suggested_actions(intent_classification.intent, conversation_id)

            # Check if confirmation is needed
            requires_confirmation = self._requires_confirmation(intent_classification.intent, conversation_id)

            # Get booking details if applicable
            booking_details = None
            if intent_classification.intent in [IntentType.BOOK_APPOINTMENT, IntentType.RESCHEDULE_APPOINTMENT]:
                booking_details = self.conversation_manager.get_booking_context(conversation_id)

            return ChatResponse(
                conversation_id=conversation_id,
                message=response_text,
                intent=intent_classification,
                suggested_actions=suggested_actions,
                requires_confirmation=requires_confirmation,
                booking_details=booking_details.dict() if booking_details else None
            )

        except Exception as e:
            logger.exception(f"Error processing message: {e}")
            if settings.DEBUG:
                error_trace = traceback.format_exc()
                return ChatResponse(
                    conversation_id=request.conversation_id or "error",
                    message=f"Error: {str(e)}\n{error_trace}",
                    intent=None
                )
            return ChatResponse(
                conversation_id=request.conversation_id or "error",
                message=(
                    "I'm sorry, I encountered an error. Please try again."
                    if not settings.DEBUG else f"Error: {str(e)}"
                ),
                intent=None
            )

    async def _generate_response_based_on_intent(
        self,
        message: str,
        intent: Any,
        conversation_id: str,
        doctor_data: List[Dict[str, Any]],
        history: List[Any]
    ) -> str:
        """Generate response based on classified intent."""

        # Check if we're in an active reschedule flow (have reschedule_in_progress flag and missing date/time)
        # If so, continue reschedule regardless of new intent classification
        conversation = self.conversation_manager.get_conversation(conversation_id)
        if conversation:
            ctx = conversation.context
            reschedule_in_progress = ctx.get("reschedule_in_progress", False)
            missing_reschedule_date = not ctx.get("reschedule_date")
            missing_reschedule_time = not ctx.get("reschedule_time")

            # If we're in a reschedule flow and still missing date/time, continue reschedule
            if reschedule_in_progress and (missing_reschedule_date or missing_reschedule_time):
                # Don't hijack if user explicitly wants to cancel or do other actions
                if intent.intent not in (IntentType.CANCEL_APPOINTMENT, IntentType.GET_DOCTOR_INFO,
                                         IntentType.CHECK_AVAILABILITY, IntentType.GET_MY_APPOINTMENTS):
                    # Check if message contains date or time entities
                    has_date_time = any(e.type in (EntityType.DATE, EntityType.TIME) for e in intent.entities)
                    if has_date_time:
                        return await self._handle_reschedule_intent(message, intent, conversation_id)

        if intent.intent == IntentType.BOOK_APPOINTMENT:
            return await self._handle_booking_intent(message, intent, conversation_id, doctor_data)

        elif intent.intent == IntentType.RESCHEDULE_APPOINTMENT:
            return await self._handle_reschedule_intent(message, intent, conversation_id)

        elif intent.intent == IntentType.CANCEL_APPOINTMENT:
            return await self._handle_cancel_intent(message, intent, conversation_id)

        elif intent.intent == IntentType.GET_DOCTOR_INFO:
            return await self._handle_doctor_info_intent(message, intent, doctor_data, conversation_id)

        elif intent.intent == IntentType.CHECK_AVAILABILITY:
            return await self._handle_availability_intent(message, intent, doctor_data, conversation_id)

        elif intent.intent == IntentType.GET_MY_APPOINTMENTS:
            return await self._handle_my_appointments_intent(conversation_id, message, doctor_data)

        else:
            # Use LLM to generate a general response
            return await self.llm_service.generate_response(
                message=message,
                intent=intent,
                context=history,
                doctor_info={"doctors": doctor_data}
            )

    async def _handle_booking_intent(
        self,
        message: str,
        intent: Any,
        conversation_id: str,
        doctor_data: List[Dict[str, Any]]
    ) -> str:
        """Handle appointment booking intent."""
        conversation = self.conversation_manager.get_conversation(conversation_id)
        context = conversation.context if conversation else {}

        # Start with existing booking context
        booking_context = self._get_existing_booking_context(context)
        previous_doctor_name = booking_context.get("doctor_name")
        previous_selected_email = booking_context.get("selected_doctor_email")

        # Extract booking details from entities and fallback parsing
        extracted = self._extract_booking_details_from_entities(intent.entities)
        explicit_doctor_name = self._match_doctor_name_in_message(message, doctor_data)
        if explicit_doctor_name:
            extracted["doctor_name"] = explicit_doctor_name
        elif extracted.get("doctor_name") and not self._mentions_doctor_pronoun(message):
            extracted.pop("doctor_name", None)

        # Validate extracted specialization - only use if explicitly mentioned in message
        # This prevents LLM from incorrectly changing the specialization mid-conversation
        if extracted.get("specialization"):
            existing_spec = booking_context.get("specialization") or context.get("last_specialization") or context.get("availability_specialization")
            extracted_spec_lower = extracted.get("specialization", "").lower()
            message_lower = message.lower()

            # Check if the extracted specialization is actually mentioned in the current message
            spec_mentioned = (
                extracted_spec_lower in message_lower or
                self._normalize_specialization(extracted_spec_lower) in message_lower
            )

            # If existing context has a specialization and new one isn't explicitly in the message, keep existing
            if existing_spec and not spec_mentioned:
                logger.info(f"Keeping existing specialization '{existing_spec}' instead of '{extracted.get('specialization')}'")
                extracted.pop("specialization", None)

        booking_context = self._merge_booking_context(booking_context, extracted)

        fallback = self._extract_booking_details_from_message(message, booking_context, context)
        booking_context = self._merge_booking_context(booking_context, fallback)

        # If user refers to a doctor pronoun, prefer last referenced doctor
        if self._mentions_doctor_pronoun(message) and context.get("last_doctor_name"):
            if not booking_context.get("doctor_name") or not self._names_match(
                booking_context.get("doctor_name"), context.get("last_doctor_name")
            ):
                booking_context["doctor_name"] = context.get("last_doctor_name")
                if context.get("last_doctor_email"):
                    booking_context["selected_doctor_email"] = context.get("last_doctor_email")
                    booking_context["doctor_email"] = context.get("last_doctor_email")

        # If user explicitly mentioned a doctor, lock selection to that doctor
        if explicit_doctor_name:
            resolved_doctor = self._find_doctor_by_name(explicit_doctor_name, doctor_data)
            if resolved_doctor:
                booking_context["doctor_name"] = resolved_doctor.get("name")
                booking_context["selected_doctor_email"] = resolved_doctor.get("email")
                booking_context["doctor_email"] = resolved_doctor.get("email")
            else:
                booking_context.pop("selected_doctor_email", None)
                booking_context.pop("doctor_email", None)

        # Clear stale email if doctor selection changed
        if (
            previous_doctor_name
            and booking_context.get("doctor_name")
            and not self._names_match(previous_doctor_name, booking_context.get("doctor_name"))
        ):
            booking_context.pop("doctor_email", None)
            booking_context.pop("selected_doctor_email", None)
            # Also clear context to prevent old doctor from being pulled back
            self.conversation_manager.update_conversation(
                conversation_id=conversation_id,
                context={
                    "last_doctor_name": booking_context.get("doctor_name"),
                    "last_doctor_email": None
                }
            )
            logger.info(f"Doctor changed from '{previous_doctor_name}' to '{booking_context.get('doctor_name')}' - clearing old context")

        # Ensure selected email still matches chosen doctor name
        if booking_context.get("selected_doctor_email") and booking_context.get("doctor_name"):
            temp_context = {
                "doctor_email": booking_context.get("selected_doctor_email"),
                "doctor_name": booking_context.get("doctor_name")
            }
            if not self._doctor_email_matches_name(temp_context, doctor_data):
                booking_context.pop("selected_doctor_email", None)
                booking_context.pop("doctor_email", None)

        # Derive doctor_email from selected_doctor_email if available
        if booking_context.get("selected_doctor_email"):
            booking_context["doctor_email"] = booking_context.get("selected_doctor_email")
            if not booking_context.get("doctor_name"):
                resolved_doctor = self._find_doctor_by_email(booking_context.get("selected_doctor_email"), doctor_data)
                if resolved_doctor:
                    booking_context["doctor_name"] = resolved_doctor.get("name")
        elif booking_context.get("doctor_name"):
            resolved_email = self._resolve_doctor_email(booking_context, doctor_data)
            if resolved_email:
                booking_context["selected_doctor_email"] = resolved_email
                booking_context["doctor_email"] = resolved_email

        # Resolve doctor/specialization from prior context if missing
        if not booking_context.get("doctor_name") and context.get("last_doctor_name"):
            booking_context["doctor_name"] = context.get("last_doctor_name")
        if (
            not booking_context.get("doctor_email")
            and context.get("last_doctor_email")
            and self._names_match(booking_context.get("doctor_name"), context.get("last_doctor_name"))
        ):
            booking_context["doctor_email"] = context.get("last_doctor_email")
            booking_context["selected_doctor_email"] = context.get("last_doctor_email")
        if not booking_context.get("specialization"):
            for key in ("last_specialization", "availability_specialization"):
                if context.get(key):
                    booking_context["specialization"] = context.get(key)
                    break

        if not booking_context.get("doctor_name"):
            resolved_doctor = self._resolve_doctor_from_context(message, context, doctor_data)
            if resolved_doctor:
                booking_context["doctor_name"] = resolved_doctor.get("name")
                booking_context["doctor_email"] = resolved_doctor.get("email")

        # Update conversation context
        self.conversation_manager.update_booking_context(conversation_id, booking_context)

        # Early phone validation: Check if user attempted to provide a phone number
        # but it was invalid (contains digits but didn't normalize properly)
        if not booking_context.get("patient_phone"):
            invalid_phone_attempt = self._detect_invalid_phone_attempt(message)
            if invalid_phone_attempt:
                self.conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    state=ConversationState.GATHERING_INFO
                )
                return (
                    "That doesn't look like a valid phone number. "
                    "Please provide a 10-digit mobile number (with optional +91 prefix)."
                )

        # Check what information we have and what's missing
        missing_info = self._get_missing_booking_info(booking_context)

        # Handle combined name+phone input when both are missing
        # User might respond with "savi, 9634927054" or "savi 9634927054"
        if (not booking_context.get("patient_name") and not booking_context.get("patient_phone")):
            extracted_name, extracted_phone = self._extract_name_and_phone_combined(message)
            if extracted_name and extracted_phone:
                booking_context["patient_name"] = extracted_name
                booking_context["patient_phone"] = extracted_phone
                self.conversation_manager.update_booking_context(
                    conversation_id,
                    {"patient_name": extracted_name, "patient_phone": extracted_phone}
                )
                missing_info = self._get_missing_booking_info(booking_context)
            elif extracted_phone and not extracted_name:
                # Got phone but not name - extract name more flexibly
                booking_context["patient_phone"] = extracted_phone
                potential_name = self._extract_name_flexible(message, extracted_phone)
                if potential_name:
                    booking_context["patient_name"] = potential_name
                    self.conversation_manager.update_booking_context(
                        conversation_id,
                        {"patient_name": potential_name, "patient_phone": extracted_phone}
                    )
                else:
                    self.conversation_manager.update_booking_context(
                        conversation_id,
                        {"patient_phone": extracted_phone}
                    )
                missing_info = self._get_missing_booking_info(booking_context)

        if missing_info and missing_info[0] == "your phone number":
            if not booking_context.get("patient_phone"):
                normalized_phone = self._normalize_phone_input(message)
                if normalized_phone:
                    booking_context["patient_phone"] = normalized_phone
                    self.conversation_manager.update_booking_context(
                        conversation_id,
                        {"patient_phone": normalized_phone}
                    )
                    missing_info = self._get_missing_booking_info(booking_context)
                elif re.search(r"\d", message):
                    self.conversation_manager.update_conversation(
                        conversation_id=conversation_id,
                        state=ConversationState.GATHERING_INFO
                    )
                    return (
                        "That doesn't look like a valid phone number. "
                        "Please provide a 10-digit mobile number (with optional +91 prefix)."
                    )

        if missing_info:
            self.conversation_manager.update_conversation(
                conversation_id=conversation_id,
                state=ConversationState.GATHERING_INFO
            )
            return self._prompt_for_missing_info(missing_info, booking_context)
        else:
            # We have all info, check availability and prepare confirmation
            return await self._check_and_confirm_booking(conversation_id, booking_context, doctor_data)

    async def _handle_reschedule_intent(self, message: str, intent: Any, conversation_id: str) -> str:
        """Handle appointment rescheduling intent."""
        # Get existing conversation context (may have appointment_id from recent booking, or partial reschedule info)
        conversation = self.conversation_manager.get_conversation(conversation_id)
        existing_context = conversation.context if conversation else {}

        # Build reschedule context, starting with existing values
        reschedule_context = {}

        # Appointment ID: prefer from existing context (from last booking or previous messages)
        existing_appointment_id = existing_context.get("appointment_id") or existing_context.get("last_appointment_id")
        if existing_appointment_id:
            reschedule_context["appointment_id"] = existing_appointment_id

        # Check if user provided appointment_id in this message (override existing)
        message_appointment_id = self._extract_appointment_id(message)
        if message_appointment_id:
            reschedule_context["appointment_id"] = message_appointment_id

        # Reschedule date: use existing if available
        if existing_context.get("reschedule_date"):
            reschedule_context["reschedule_date"] = existing_context.get("reschedule_date")

        # Reschedule time: use existing if available
        if existing_context.get("reschedule_time"):
            reschedule_context["reschedule_time"] = existing_context.get("reschedule_time")

        # Extract date/time entities from current message (override existing)
        new_details = self._extract_reschedule_details(intent.entities)
        reschedule_context.update(new_details)

        # Fallback: try to extract date/time directly from message text if not found in entities
        if not reschedule_context.get("reschedule_date"):
            fallback_date = self._extract_date_from_text(message)
            if fallback_date:
                reschedule_context["reschedule_date"] = fallback_date

        if not reschedule_context.get("reschedule_time"):
            fallback_time = self._extract_time_from_text(message)
            if fallback_time:
                reschedule_context["reschedule_time"] = fallback_time

        # Store merged context and mark that we're in a reschedule flow
        reschedule_context["reschedule_in_progress"] = True
        self.conversation_manager.update_booking_context(conversation_id, reschedule_context)

        # Check what's still missing
        missing_info = []
        if not reschedule_context.get("appointment_id"):
            missing_info.append("your appointment ID")
        if not reschedule_context.get("reschedule_date"):
            missing_info.append("the new date")
        if not reschedule_context.get("reschedule_time"):
            missing_info.append("the new time")

        if missing_info:
            return f"I can help reschedule that. I still need {', '.join(missing_info)}."

        # All info collected - move to confirmation (clear the in_progress flag)
        self.conversation_manager.update_conversation(
            conversation_id=conversation_id,
            state=ConversationState.CONFIRMING_BOOKING,
            context={"pending_action": "reschedule", "reschedule_in_progress": False}
        )
        return (
            "Please confirm: I will reschedule your appointment to "
            f"{reschedule_context.get('reschedule_date')} at {reschedule_context.get('reschedule_time')}. "
            "Reply with 'yes' to proceed or 'no' to cancel."
        )

    async def _handle_cancel_intent(self, message: str, intent: Any, conversation_id: str) -> str:
        """Handle appointment cancellation intent."""
        # Get existing conversation context (may have appointment_id from recent booking)
        conversation = self.conversation_manager.get_conversation(conversation_id)
        existing_context = conversation.context if conversation else {}

        # Check if user provided appointment_id in this message
        appointment_id = self._extract_appointment_id(message)

        # If not in message, check existing context (from last booking)
        if not appointment_id:
            appointment_id = existing_context.get("appointment_id") or existing_context.get("last_appointment_id")

        if appointment_id:
            self.conversation_manager.update_booking_context(
                conversation_id,
                {"appointment_id": appointment_id}
            )
            self.conversation_manager.update_conversation(
                conversation_id=conversation_id,
                state=ConversationState.CONFIRMING_BOOKING,
                context={"pending_action": "cancel"}
            )
            return (
                f"Please confirm: I will cancel appointment {appointment_id}. "
                "Reply with 'yes' to proceed or 'no' to cancel."
            )

        return "I'd be happy to help you cancel your appointment. Please provide your appointment ID."

    async def _handle_doctor_info_intent(
        self,
        message: str,
        intent: Any,
        doctor_data: List[Dict[str, Any]],
        conversation_id: str
    ) -> str:
        """Handle doctor information requests."""
        if not doctor_data or not isinstance(doctor_data, list):
            return "I'm having trouble accessing doctor information right now. Please try again in a moment."

        conversation = self.conversation_manager.get_conversation(conversation_id)
        context = conversation.context if conversation else {}

        # Look for specialization or doctor name in entities
        specialization = None
        doctor_name = None

        for entity in intent.entities:
            if entity.type == EntityType.SPECIALIZATION:
                specialization = entity.value
            elif entity.type == EntityType.DOCTOR_NAME:
                doctor_name = entity.value

        explicit_doctor_name = self._match_doctor_name_in_message(message, doctor_data)
        if explicit_doctor_name:
            doctor_name = explicit_doctor_name
        elif doctor_name and not self._mentions_doctor_pronoun(message):
            # Avoid LLM-inferred doctor when user didn't mention one
            doctor_name = None

        if not doctor_name:
            resolved_doctor = self._resolve_doctor_from_context(message, context, doctor_data)
            if resolved_doctor:
                doctor_name = resolved_doctor.get("name")

        if not specialization:
            specialization = self._guess_specialization_from_text(message, doctor_data)

        if not specialization and context.get("last_specialization") and self._mentions_doctor_pronoun(message):
            specialization = context.get("last_specialization")

        # Handle "tell me more", "yes", etc. when we have context about a doctor/specialization
        wants_more_info = self._wants_more_information(message)
        wants_all_info = self._wants_info_about_all(message)

        if not doctor_name and not specialization:
            candidates = context.get("doctor_info_candidates") or []
            last_doctor = context.get("last_doctor_name")
            last_spec = context.get("last_specialization")

            # If user says "tell me about both/them/all", show info for ALL candidates
            if wants_all_info and candidates and len(candidates) > 1:
                return self._format_multiple_doctors_info(candidates, doctor_data, conversation_id)

            # If user says "yes" or "tell me more" and we have a single candidate, show their info
            if (self._is_affirmative(message) or wants_more_info) and candidates:
                if len(candidates) == 1:
                    # Only one doctor - show their details directly
                    doctor_name = candidates[0]
                elif wants_more_info and len(candidates) > 1:
                    # User said "tell me more" with multiple candidates - show all
                    return self._format_multiple_doctors_info(candidates, doctor_data, conversation_id)
                elif context.get("awaiting_doctor_info"):
                    candidate_names = [self._format_doctor_name(name) for name in candidates[:3]]
                    return (
                        "Which doctor would you like more information about? "
                        f"I have {', '.join(candidate_names)}."
                    )

            # If user says "tell me more" and we have last doctor context, use it
            if not doctor_name and wants_more_info and last_doctor:
                doctor_name = last_doctor

            # If user says "tell me more" and we have specialization context but no doctor
            if not doctor_name and not specialization and wants_more_info and last_spec:
                specialization = last_spec

        if doctor_name:
            # Find specific doctor - use flexible matching
            doctor = self._find_doctor_by_name(doctor_name, doctor_data)
            if doctor:
                self.conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    context={
                        "awaiting_doctor_info": False,
                        "last_doctor_name": doctor.get("name"),
                        "last_doctor_email": doctor.get("email"),
                        "last_specialization": doctor.get("specialization") or context.get("last_specialization")
                    }
                )
                languages = self._safe_list(doctor.get("languages"))
                working_days = self._safe_list(doctor.get("working_days"))
                working_hours = doctor.get("working_hours") or {}
                display_name = self._format_doctor_name(doctor.get("name"))
                specialization_text = doctor.get('specialization', 'specialist')

                # Determine pronoun based on name (simple heuristic for common names)
                pronoun = self._get_doctor_pronoun(doctor.get("name"))
                pronoun_caps = pronoun.capitalize()

                # Check if user is asking a yes/no question about this doctor
                is_yes_no_question = self._is_yes_no_question_about_doctor(message)
                prefix = ""
                if is_yes_no_question:
                    prefix = f"Yes, {display_name} is available in our network. "

                # Format working days with capitalization
                formatted_days = ', '.join([d.capitalize() for d in working_days]) if working_days else 'select days'

                return (
                    f"{prefix}{display_name} specializes in {specialization_text} "
                    f"and has {doctor.get('experience_years', 'several')} years of experience. "
                    f"{pronoun_caps} speaks {', '.join(languages) if languages else 'multiple languages'} "
                    f"and is available {formatted_days} "
                    f"from {working_hours.get('start', 'N/A')} to {working_hours.get('end', 'N/A')}."
                )
            else:
                self.conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    context={"awaiting_doctor_info": False}
                )
                return f"I couldn't find a doctor named {doctor_name} in our network. Let me show you our available doctors."

        elif specialization:
            # Find doctors by specialization
            normalized_specialization = self._normalize_specialization(specialization)
            matching_doctors = [
                d for d in doctor_data
                if self._match_specialization(d.get("specialization") or "", normalized_specialization)
            ]
            if matching_doctors:
                self._store_doctor_candidates(conversation_id, matching_doctors, normalized_specialization)

                if len(matching_doctors) == 1:
                    # Auto-show doctor info when only one candidate
                    doctor = matching_doctors[0]
                    display_name = self._format_doctor_name(doctor.get("name"))
                    languages = self._safe_list(doctor.get("languages"))
                    working_days = self._safe_list(doctor.get("working_days"))
                    working_hours = doctor.get("working_hours") or {}
                    pronoun = self._get_doctor_pronoun(doctor.get("name"))
                    pronoun_caps = pronoun.capitalize()
                    formatted_days = ', '.join([d.capitalize() for d in working_days]) if working_days else 'select days'

                    # Update context with this doctor's info
                    self.conversation_manager.update_conversation(
                        conversation_id=conversation_id,
                        context={
                            "awaiting_doctor_info": False,
                            "last_doctor_name": doctor.get("name"),
                            "last_doctor_email": doctor.get("email"),
                            "last_specialization": doctor.get("specialization") or normalized_specialization
                        }
                    )

                    return (
                        f"For {specialization}, we have {display_name}. "
                        f"{pronoun_caps} has {doctor.get('experience_years', 'several')} years of experience "
                        f"and speaks {', '.join(languages) if languages else 'multiple languages'}. "
                        f"{pronoun_caps} is available {formatted_days} "
                        f"from {working_hours.get('start', 'N/A')} to {working_hours.get('end', 'N/A')}. "
                        f"Would you like to book an appointment?"
                    )
                else:
                    doctor_names = [self._format_doctor_name(d.get("name")) for d in matching_doctors[:3]]
                    return f"For {specialization}, we have: {', '.join(doctor_names)}. Would you like more information about any of them?"
            else:
                self.conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    context={
                        "awaiting_doctor_info": False,
                        "last_specialization": normalized_specialization or specialization
                    }
                )
                return f"I don't have doctors specializing in {specialization} at the moment. Let me show you our available specializations."

        else:
            # General doctor info
            specializations = [
                d.get("specialization") for d in doctor_data
                if isinstance(d, dict) and d.get("specialization")
            ]
            specializations = list(set(specializations))
            if not specializations:
                return "I don't have any specialization data yet. Please try again later."
            self.conversation_manager.update_conversation(
                conversation_id=conversation_id,
                context={"awaiting_doctor_info": False}
            )
            return f"We have doctors specializing in: {', '.join(specializations)}. Which area are you interested in?"

    async def _handle_availability_intent(
        self,
        message: str,
        intent: Any,
        doctor_data: List[Dict[str, Any]],
        conversation_id: str
    ) -> str:
        """Handle availability checking intent."""
        if not doctor_data or not isinstance(doctor_data, list):
            return "I'm having trouble accessing doctor information right now. Please try again in a moment."

        conversation = self.conversation_manager.get_conversation(conversation_id)
        context = conversation.context if conversation else {}

        doctor_name = None
        specialization = None
        requested_date = None

        for entity in intent.entities:
            if entity.type == EntityType.DOCTOR_NAME:
                doctor_name = entity.value
            elif entity.type == EntityType.SPECIALIZATION:
                specialization = entity.value
            elif entity.type == EntityType.DATE:
                requested_date = entity.value

        if not doctor_name:
            doctor_name = self._match_doctor_name_in_message(message, doctor_data)

        if not doctor_name and self._mentions_doctor_pronoun(message):
            doctor_name = context.get("last_doctor_name")

        if not specialization:
            specialization = self._guess_specialization_from_text(message, doctor_data)

        if not specialization:
            specialization = context.get("availability_specialization") or context.get("last_specialization")

        if not requested_date:
            # Try to extract date from message more intelligently
            requested_date = self._extract_date_from_message(message)

        date_obj = self._parse_date(requested_date)
        update_context = {}
        if specialization:
            update_context["availability_specialization"] = self._normalize_specialization(specialization)
            update_context["last_specialization"] = self._normalize_specialization(specialization)
        if doctor_name:
            update_context["last_doctor_name"] = doctor_name
            resolved_email = self._resolve_doctor_email({"doctor_name": doctor_name}, doctor_data)
            if resolved_email:
                update_context["last_doctor_email"] = resolved_email
        if date_obj:
            update_context["availability_date"] = date_obj.isoformat()
        if update_context:
            self.conversation_manager.update_conversation(
                conversation_id=conversation_id,
                context=update_context
            )

        if not date_obj:
            # Check if user is asking about timing constraints (e.g., "is he not available for evening?")
            is_timing_question, time_period = self._is_timing_constraint_question(message)

            if is_timing_question:
                # Try to use context to answer the timing question
                context_doctor_name = doctor_name or context.get("last_doctor_name")
                context_doctor_email = context.get("last_doctor_email")

                if context_doctor_name or context_doctor_email:
                    # Find the doctor to get working hours
                    target_doctor = None
                    if context_doctor_email:
                        target_doctor = self._find_doctor_by_email(context_doctor_email, doctor_data)
                    elif context_doctor_name:
                        target_doctor = self._find_doctor_by_name(context_doctor_name, doctor_data)

                    if target_doctor:
                        working_hours = target_doctor.get("working_hours", {})
                        work_start = working_hours.get("start", "09:00")
                        work_end = working_hours.get("end", "17:00")
                        doctor_display = self._format_doctor_name(target_doctor.get("name"))

                        # Format working hours for display
                        start_formatted = self._format_slot_time(work_start)
                        end_formatted = self._format_slot_time(work_end)

                        if time_period == "evening":
                            return (
                                f"{doctor_display}'s working hours are {start_formatted} to {end_formatted}, "
                                f"so evening appointments after {end_formatted} are not available. "
                                f"Would you like to book within these hours, or should I check another doctor?"
                            )
                        elif time_period == "afternoon":
                            # Check if afternoon is within working hours
                            try:
                                end_hour = int(work_end.split(":")[0])
                                if end_hour <= 12:
                                    return (
                                        f"{doctor_display}'s working hours are {start_formatted} to {end_formatted}, "
                                        f"so afternoon slots are not available. "
                                        f"Would you like a morning appointment, or should I check another doctor?"
                                    )
                                else:
                                    return (
                                        f"{doctor_display} is available in the afternoon until {end_formatted}. "
                                        f"Working hours are {start_formatted} to {end_formatted}. "
                                        f"What date would you like to check for afternoon availability?"
                                    )
                            except (ValueError, IndexError) as e:
                                logger.warning(f"Failed to parse working hours end time '{work_end}': {e}")
                                pass
                        elif time_period == "morning":
                            return (
                                f"{doctor_display} is available in the morning from {start_formatted}. "
                                f"Working hours are {start_formatted} to {end_formatted}. "
                                f"What date would you like to check?"
                            )
                        else:
                            return (
                                f"{doctor_display}'s working hours are {start_formatted} to {end_formatted}. "
                                f"I can only show available slots within these hours. "
                                f"What date would you like to check availability?"
                            )

            # Default behavior - ask for date
            if specialization:
                return f"For {specialization}, what date would you like to check availability for?"
            return "Please tell me the date you want to check availability for."

        if not doctor_name and not specialization:
            specializations = self._get_unique_specializations(doctor_data)
            if specializations:
                return (
                    f"Which specialty would you like to check on {date_obj.isoformat()}? "
                    f"We currently have: {', '.join(specializations)}."
                )
            return "Which specialty would you like to check availability for?"

        async with CalendarClient() as calendar_client:
            if doctor_name:
                doctor_email = self._resolve_doctor_email({"doctor_name": doctor_name}, doctor_data)
                if not doctor_email:
                    return f"I couldn't find a doctor named {doctor_name}. Please specify another doctor or specialty."

                availability = await calendar_client.get_doctor_availability(doctor_email, date_obj)
                slots = availability.get("available_slots", [])
                if not slots:
                    return (
                        f"{self._format_doctor_name(doctor_name)} has no available slots on {date_obj.isoformat()}. "
                        "Would you like to check another date or a different doctor?"
                    )

                # Persist availability context for booking follow-ups
                self.conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    context={
                        "availability_date": date_obj.isoformat(),
                        "last_doctor_name": doctor_name,
                        "last_doctor_email": doctor_email,
                        "availability_specialization": specialization or context.get("last_specialization")
                    }
                )

                slots_text = self._format_slots(slots, target_date=date_obj)
                date_display = self._format_date_display(date_obj.isoformat())
                return f"{self._format_doctor_name(doctor_name)} is available on {date_display}:\n{slots_text}"

            if specialization:
                normalized_specialization = self._normalize_specialization(specialization)
                availability = await calendar_client.check_availability(
                    date=date_obj,
                    specialization=normalized_specialization
                )
                doctors = availability.get("doctors", [])
                if not doctors:
                    return f"I couldn't find any doctors for {specialization}. Would you like a different specialty?"

                available_doctors = [
                    d for d in doctors
                    if isinstance(d, dict) and d.get("is_available")
                ]
                if not available_doctors:
                    return (
                        f"No {specialization} doctors have availability on {date_obj.isoformat()}. "
                        "Would you like to try another date?"
                    )

                # Persist availability context for booking follow-ups
                availability_context: Dict[str, Any] = {
                    "availability_date": date_obj.isoformat(),
                    "availability_specialization": normalized_specialization
                }
                if len(available_doctors) == 1:
                    availability_context["last_doctor_name"] = available_doctors[0].get("name")
                    availability_context["last_doctor_email"] = available_doctors[0].get("email")
                self.conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    context=availability_context
                )

                summaries = []
                date_display = self._format_date_display(date_obj.isoformat())
                for doctor in available_doctors[:3]:
                    slots_text = self._format_slots(doctor.get("available_slots", []), target_date=date_obj)
                    summaries.append(f"\n\n👨‍⚕️ {self._format_doctor_name(doctor.get('name'))}:\n{slots_text}")

                return f"Available {specialization} doctors on {date_display}:" + "".join(summaries)

        return "Please tell me which doctor or specialty you'd like and the date you're looking for."

    async def _handle_my_appointments_intent(self, conversation_id: str, message: str = "", doctor_data: List[Dict[str, Any]] = None) -> str:
        """Handle requests for user's appointments."""
        conversation = self.conversation_manager.get_conversation(conversation_id)
        context = conversation.context if conversation else {}

        phone = context.get("patient_phone")
        if not phone:
            # Try to extract phone number from recent message context
            history = self.conversation_manager.get_conversation_history(conversation_id, limit=5)
            for msg in reversed(history):
                if msg.role.value == "user":
                    phone = self._extract_phone_anywhere(msg.content)
                    if phone:
                        break

        if not phone:
            return "Please provide your phone number so I can look up your appointments."

        self.conversation_manager.update_conversation(
            conversation_id=conversation_id,
            context={"patient_phone": phone}
        )

        # Check if user wants appointments with a specific doctor
        filter_doctor_name = None
        if doctor_data and message:
            filter_doctor_name = self._match_doctor_name_in_message(message, doctor_data)

        try:
            async with CalendarClient() as calendar_client:
                patient = await calendar_client.get_patient_by_mobile(phone)
                if not patient or patient.get("error"):
                    return "I couldn't find a patient with that phone number. Please check the number and try again."

                patient_id = patient.get("id")
                if not patient_id:
                    return "I couldn't find a patient record for that phone number."

                appointments = await calendar_client.get_patient_appointments(patient_id)
                if not appointments:
                    return "I couldn't find any appointments for that phone number."

                # Filter by doctor name if specified
                if filter_doctor_name:
                    appointments = [
                        appt for appt in appointments
                        if self._names_match(appt.get("doctor_name", ""), filter_doctor_name)
                    ]
                    if not appointments:
                        return f"You don't have any appointments with {self._format_doctor_name(filter_doctor_name)}."

                summaries = []
                for appt in appointments[:10]:
                    doctor_name = appt.get("doctor_name", "Unknown Doctor")
                    appt_date = self._format_date_display(appt.get("date"))
                    appt_time = self._format_slot_time(appt.get("start_time", ""))
                    status = appt.get("status", "").capitalize()
                    summaries.append(
                        f"• {self._format_doctor_name(doctor_name)} - {appt_date} at {appt_time} ({status})\n  ID: {appt.get('id')}"
                    )

                header = "Here are your appointments"
                if filter_doctor_name:
                    header += f" with {self._format_doctor_name(filter_doctor_name)}"
                header += ":\n\n"

                return header + "\n".join(summaries)
        except Exception as e:
            logger.error(f"Error fetching appointments: {e}")
            return "I couldn't fetch your appointments right now. Please try again."

    def _extract_booking_details_from_entities(self, entities: List[Any]) -> Dict[str, Any]:
        """Extract booking details from entities."""
        booking_details = {}

        for entity in entities:
            if entity.type == EntityType.DOCTOR_NAME:
                # Find doctor by name (would need doctor data)
                booking_details["doctor_name"] = entity.value
            elif entity.type == EntityType.SPECIALIZATION:
                booking_details["specialization"] = entity.value
            elif entity.type == EntityType.DATE:
                booking_details["date"] = entity.value
            elif entity.type == EntityType.TIME:
                booking_details["time"] = entity.value
            elif entity.type == EntityType.PATIENT_NAME:
                # Validate patient_name is not actually a symptom
                if not self._is_likely_symptom(entity.value):
                    booking_details["patient_name"] = entity.value
                else:
                    # If LLM mistakenly classified a symptom as patient_name, treat as symptom
                    logger.info(f"Reclassifying '{entity.value}' from patient_name to symptoms")
                    if "symptoms" not in booking_details:
                        booking_details["symptoms"] = entity.value
            elif entity.type == EntityType.PHONE_NUMBER:
                normalized = self._normalize_phone_input(entity.value)
                if normalized:
                    booking_details["patient_phone"] = normalized
            elif entity.type == EntityType.EMAIL:
                booking_details["patient_email"] = entity.value
            elif entity.type == EntityType.SYMPTOMS:
                booking_details["symptoms"] = entity.value

        return booking_details

    def _extract_reschedule_details(self, entities: List[Any]) -> Dict[str, Any]:
        """Extract reschedule details from entities."""
        reschedule_details = {}
        for entity in entities:
            if entity.type == EntityType.DATE:
                reschedule_details["reschedule_date"] = entity.value
            elif entity.type == EntityType.TIME:
                reschedule_details["reschedule_time"] = entity.value

        return reschedule_details

    def _get_missing_booking_info(self, booking_details: Dict[str, Any]) -> List[str]:
        """Get list of missing information for booking."""
        # Order matters: ask core booking details before patient contact
        required_fields = ["doctor_or_specialization", "date", "time", "patient_name", "patient_phone"]
        missing = []

        for field in required_fields:
            if field == "doctor_or_specialization":
                if booking_details.get("doctor_name") or booking_details.get("specialization") or booking_details.get("doctor_email"):
                    continue
            elif booking_details.get(field):
                continue

            if field == "doctor_or_specialization":
                missing.append("the doctor or specialization")
            else:
                # Convert to user-friendly names
                field_names = {
                    "patient_name": "your name",
                    "patient_phone": "your phone number",
                    "date": "the appointment date",
                    "time": "the appointment time"
                }
                missing.append(field_names.get(field, field))

        return missing

    def _prompt_for_missing_info(self, missing_info: List[str], booking_context: Dict[str, Any]) -> str:
        """Ask for the next missing piece of booking info with context - optimized for natural flow."""
        if not missing_info:
            return "What details would you like to provide?"

        # Group related fields for natural conversation flow
        if len(missing_info) >= 2:
            # Ask for name and phone together
            if "your name" in missing_info and "your phone number" in missing_info:
                doctor_text = ""
                if booking_context.get("doctor_name"):
                    doctor_text = f" with {self._format_doctor_name(booking_context.get('doctor_name'))}"
                elif booking_context.get("specialization"):
                    doctor_text = f" for {booking_context.get('specialization')}"
                    
                date_time_text = ""
                if booking_context.get("date") and booking_context.get("time"):
                    date_time_text = f" on {booking_context.get('date')} at {booking_context.get('time')}"
                elif booking_context.get("date"):
                    date_time_text = f" on {booking_context.get('date')}"
                    
                return f"Great! I just need your name and phone number to book the appointment{doctor_text}{date_time_text}."
            
            # Ask for date and time together
            if "the appointment date" in missing_info and "the appointment time" in missing_info:
                doctor_text = ""
                if booking_context.get("doctor_name"):
                    doctor_text = f" with {self._format_doctor_name(booking_context.get('doctor_name'))}"
                elif booking_context.get("specialization"):
                    doctor_text = f" for {booking_context.get('specialization')}"
                    
                return f"What date and time would work for you{doctor_text}?"

        # Single field prompts
        primary = missing_info[0]
        
        # Build context summary
        context_parts = []
        if booking_context.get("doctor_name"):
            context_parts.append(f"{self._format_doctor_name(booking_context.get('doctor_name'))}")
        elif booking_context.get("specialization"):
            context_parts.append(f"{booking_context.get('specialization')}")
        if booking_context.get("date"):
            context_parts.append(f"{booking_context.get('date')}")
        if booking_context.get("time"):
            context_parts.append(f"{booking_context.get('time')}")

        context_text = f"for {' on '.join(context_parts)}" if context_parts else ""

        if primary == "the doctor or specialization":
            return "Which doctor or specialty would you like to book?"
        if primary == "the appointment date":
            return f"What date should I book the appointment {context_text}?"
        if primary == "the appointment time":
            return f"What time works for you{' on ' + booking_context.get('date') if booking_context.get('date') else ''}?"
        if primary == "your name":
            return f"May I have your name{' ' + context_text if context_text else ''}?"
        if primary == "your phone number":
            return f"And your phone number{' ' + context_text if context_text else ''}?"

        return f"Please provide {primary}."

    def _get_existing_booking_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get persisted booking context fields only."""
        booking_context = {}
        for field in self.BOOKING_CONTEXT_FIELDS:
            if field in context and context.get(field) not in [None, ""]:
                booking_context[field] = context.get(field)
        return booking_context

    def _merge_booking_context(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """Merge updates into booking context, skipping empty values."""
        merged = dict(base)
        for key, value in (updates or {}).items():
            if value not in [None, ""]:
                merged[key] = value
        return merged

    def _build_idempotency_key(self, action: str, payload: Dict[str, Any], salt: Optional[str] = None) -> str:
        enriched = dict(payload)
        if salt:
            enriched["_salt"] = salt
        raw = json.dumps(enriched, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        return f"{action}:{digest}"

    def _normalize_phone_input(self, value: Optional[str]) -> Optional[str]:
        """Normalize phone input to 10 digits or +91XXXXXXXXXX.

        Handles various formats:
        - Pure 10 digits: 9876543210
        - With spaces/dashes: 987-654-3210, 987 654 3210
        - With country code: +919876543210, +91 9876543210, 919876543210
        - With leading zero: 09876543210
        """
        if not value:
            return None

        # First, try to find a phone number pattern in the text
        # Match patterns like +91..., 91..., or 10-digit numbers with optional separators
        phone_patterns = [
            r'\+91[\s\-]?(\d{10})',           # +91 followed by 10 digits
            r'\b91[\s\-]?(\d{10})\b',          # 91 followed by 10 digits
            r'\+91[\s\-]?(\d[\d\s\-]{8,}\d)',  # +91 with separators
            r'\b0?(\d{10})\b',                 # 10 digits with optional leading 0
            r'\b(\d{3}[\s\-]\d{3}[\s\-]\d{4})\b',  # XXX-XXX-XXXX format
            r'\b(\d{5}[\s\-]\d{5})\b',         # XXXXX-XXXXX format
        ]

        for pattern in phone_patterns:
            match = re.search(pattern, value)
            if match:
                captured = match.group(1) if match.lastindex else match.group(0)
                digits = re.sub(r'\D', '', captured)
                if len(digits) == 10:
                    # Check if original had +91 prefix
                    full_match = match.group(0)
                    if full_match.startswith('+91'):
                        return f"+91{digits}"
                    return digits

        # Fallback: extract all digits and check if we have exactly 10 or 12 (with 91)
        cleaned = re.sub(r"[^\d+]", "", value)
        if cleaned.startswith("++"):
            cleaned = cleaned[1:]
        has_plus = cleaned.startswith("+")
        digits = re.sub(r"\D", "", cleaned)

        # Handle +91XXXXXXXXXX format
        if has_plus and len(digits) == 12 and digits.startswith("91"):
            return f"+{digits}"

        # Handle 91XXXXXXXXXX without plus
        if len(digits) == 12 and digits.startswith("91"):
            return f"+{digits}"

        # Handle pure 10-digit number
        if len(digits) == 10:
            return digits

        # Handle 11 digits starting with 0 (leading zero)
        if len(digits) == 11 and digits.startswith("0"):
            return digits[1:]

        return None

    def _extract_booking_details_from_message(
        self,
        message: str,
        booking_context: Dict[str, Any],
        conversation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback extraction for booking details directly from text."""
        extracted: Dict[str, Any] = {}
        if not message:
            return extracted

        if not booking_context.get("patient_phone"):
            phone = self._extract_phone_from_text(message)
            if phone:
                extracted["patient_phone"] = phone

        if not booking_context.get("patient_name"):
            name = self._extract_name_from_text(message)
            if name:
                extracted["patient_name"] = name

        if not booking_context.get("date"):
            date_value = self._extract_date_from_text(message)
            if date_value:
                extracted["date"] = date_value

        # Always try to extract time - user may be providing a NEW time after a slot was unavailable
        # This allows natural conversation flow like "try 2pm instead"
        time_value = self._extract_time_from_text(message)
        if time_value:
            extracted["time"] = time_value

        if not booking_context.get("doctor_name") and self._mentions_doctor_pronoun(message):
            if conversation_context.get("last_doctor_name"):
                extracted["doctor_name"] = conversation_context.get("last_doctor_name")
            if conversation_context.get("last_doctor_email"):
                extracted["doctor_email"] = conversation_context.get("last_doctor_email")

        if not booking_context.get("specialization") and self._mentions_doctor_pronoun(message):
            if conversation_context.get("last_specialization"):
                extracted["specialization"] = conversation_context.get("last_specialization")

        return extracted

    def _extract_phone_from_text(self, message: str) -> Optional[str]:
        """Extract phone number from text when explicitly mentioned."""
        if not re.search(r"\b(phone|mobile|number|call me)\b", message, re.IGNORECASE):
            return None
        return self._normalize_phone_input(message)

    def _extract_phone_anywhere(self, message: Optional[str]) -> Optional[str]:
        """Extract phone number from text without requiring keywords."""
        return self._normalize_phone_input(message)

    def _detect_invalid_phone_attempt(self, message: str) -> bool:
        """Detect if user attempted to provide a phone number but it's invalid.

        Returns True if the message contains a sequence of digits that looks like
        a phone number attempt but doesn't normalize to a valid phone.
        """
        if not message:
            return False

        # Look for digit sequences that might be phone attempts
        # A phone attempt is: 4+ consecutive digits (ignoring spaces/dashes)
        digit_sequences = re.findall(r'[\d\s\-]{4,}', message)
        if not digit_sequences:
            return False

        for seq in digit_sequences:
            digits_only = re.sub(r'\D', '', seq)
            # If we have 4-9 or 11+ digits (not 10, not 12 with 91), it's invalid
            if len(digits_only) >= 4:
                # Check if it's a valid time (like 11:30 -> 1130, or 3rd feb -> 3)
                if len(digits_only) <= 4 and re.search(r'\d{1,2}[:\s]?\d{2}', seq):
                    continue  # This is likely a time, not a phone
                if len(digits_only) <= 2:
                    continue  # Too short, likely date/time component

                # Check if this would normalize to a valid phone
                normalized = self._normalize_phone_input(seq)
                if normalized is None and len(digits_only) >= 6:
                    # Has 6+ digits but doesn't normalize - invalid phone attempt
                    return True

        return False

    def _extract_name_from_text(self, message: str) -> Optional[str]:
        """Extract name from text patterns like 'my name is'."""
        # Common symptom/condition words that should NOT be treated as names
        symptom_words = {
            "facing", "having", "suffering", "experiencing", "getting",
            "allergy", "allergies", "rash", "itching", "pain", "ache",
            "fever", "cough", "cold", "headache", "stomach", "skin",
            "issue", "problem", "condition", "sick", "unwell", "ill",
            "burning", "swelling", "infection", "irritation", "discomfort"
        }

        match = re.search(r"\bmy name is\s+([a-zA-Z][a-zA-Z\s'.-]{1,50})", message, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Validate it's not a symptom word
            if not any(word in name.lower() for word in symptom_words):
                return name

        match = re.search(r"\bi am\s+([a-zA-Z][a-zA-Z\s'.-]{1,50})", message, re.IGNORECASE)
        if match:
            potential_name = match.group(1).strip()
            # Exclude phrases like "i am facing", "i am having", "i am looking for"
            if re.search(r"\b(looking for|seeking|searching|facing|having|suffering|experiencing|getting)\b", potential_name, re.IGNORECASE):
                return None
            # Exclude if it contains symptom words
            if any(word in potential_name.lower() for word in symptom_words):
                return None
            return potential_name
        return None

    def _extract_name_and_phone_combined(self, message: str) -> tuple:
        """Extract name and phone from combined formats like 'savi, 9634927054' or 'savi 9634927054'.

        Returns tuple of (name, phone) where either can be None if not found.
        """
        if not message:
            return None, None

        # First extract phone number
        phone = self._normalize_phone_input(message)
        if not phone:
            return None, None

        # Common words to exclude from names
        exclude_words = {
            "my", "name", "is", "phone", "number", "mobile", "call", "me", "at",
            "and", "the", "i", "am", "yes", "no", "ok", "okay", "hi", "hello",
            "book", "appointment", "doctor", "with"
        }

        # Find where phone number starts in message
        # Match various phone formats
        phone_patterns = [
            r'\+91[\s\-]?\d{10}',
            r'\b91[\s\-]?\d{10}\b',
            r'\b0?\d{10}\b',
            r'\b\d{3}[\s\-]\d{3}[\s\-]\d{4}\b',
            r'\b\d{5}[\s\-]\d{5}\b',
        ]

        phone_start = len(message)
        for pattern in phone_patterns:
            match = re.search(pattern, message)
            if match:
                phone_start = min(phone_start, match.start())
                break

        # Get text before phone number
        text_before_phone = message[:phone_start].strip()

        # Clean up the text - remove common prefixes and separators
        text_before_phone = re.sub(r'^(my name is|i am|name:|name)\s*', '', text_before_phone, flags=re.IGNORECASE)
        text_before_phone = text_before_phone.rstrip(',').rstrip('-').strip()

        if not text_before_phone:
            return None, phone

        # Extract potential name (first word or words before phone)
        words = text_before_phone.split()
        name_words = []
        for word in words:
            word_clean = word.lower().strip('.,!?')
            if word_clean not in exclude_words and len(word_clean) > 1:
                # Check if it looks like a name (starts with letter, mostly letters)
                if re.match(r'^[a-zA-Z][a-zA-Z\s\'.-]*$', word):
                    name_words.append(word)

        if name_words:
            name = ' '.join(name_words).strip()
            # Title case the name
            name = ' '.join(w.capitalize() for w in name.split())
            return name, phone

        return None, phone

    def _extract_name_flexible(self, message: str, phone_to_exclude: str = None) -> Optional[str]:
        """Extract name more flexibly when we know we're looking for a name.

        Used when phone is already extracted and we need to find the name part.
        """
        if not message:
            return None

        # Remove phone number from message if provided
        text = message
        if phone_to_exclude:
            # Remove various formats of the phone
            digits = re.sub(r'\D', '', phone_to_exclude)
            if len(digits) >= 10:
                core_digits = digits[-10:]  # Last 10 digits
                # Remove the phone number in various formats
                patterns = [
                    rf'\+?91[\s\-]?{core_digits}',
                    rf'\b0?{core_digits}\b',
                    rf'{core_digits[:3]}[\s\-]?{core_digits[3:6]}[\s\-]?{core_digits[6:]}',
                ]
                for pattern in patterns:
                    text = re.sub(pattern, '', text)

        # Clean up separators and common words
        text = text.strip().rstrip(',').rstrip('-').strip()
        text = re.sub(r'^(my name is|i am|name:|name)\s*', '', text, flags=re.IGNORECASE)
        text = text.strip()

        if not text:
            return None

        # Exclude words
        exclude_words = {
            "my", "name", "is", "phone", "number", "mobile", "call", "me", "at",
            "and", "the", "yes", "no", "ok", "okay", "hi", "hello"
        }

        words = text.split()
        name_words = []
        for word in words:
            word_clean = word.lower().strip('.,!?')
            if word_clean not in exclude_words and len(word_clean) > 1:
                if re.match(r'^[a-zA-Z][a-zA-Z\'.-]*$', word):
                    name_words.append(word)

        if name_words:
            name = ' '.join(name_words).strip()
            name = ' '.join(w.capitalize() for w in name.split())
            return name

        return None

    def _is_likely_symptom(self, value: str) -> bool:
        """Check if a value looks like a symptom rather than a name."""
        if not value:
            return False

        symptom_indicators = [
            "allergy", "allergies", "rash", "itching", "itch", "pain", "ache",
            "fever", "cough", "cold", "headache", "stomach", "skin", "issue",
            "problem", "condition", "burning", "swelling", "infection", "irritation",
            "discomfort", "nausea", "vomiting", "diarrhea", "fatigue", "weakness",
            "dizziness", "bleeding", "inflammation", "soreness", "cramp", "spasm"
        ]

        value_lower = value.lower()
        return any(word in value_lower for word in symptom_indicators)

    def _extract_date_from_text(self, message: str) -> Optional[str]:
        """Extract date text using heuristics."""
        if not re.search(
            r"\b(today|tomorrow|next|monday|tuesday|wednesday|thursday|friday|saturday|sunday|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{1,2}[/-]\d{1,2}|\d{4}-\d{1,2}-\d{1,2})\b",
            message,
            re.IGNORECASE
        ):
            return None
        date_obj = self._parse_date(message)
        return date_obj.isoformat() if date_obj else None

    def _extract_time_from_text(self, message: str) -> Optional[str]:
        """Extract time text using heuristics."""
        if not re.search(r"\b\d{1,2}(:\d{2})?\s*(am|pm)\b|\b\d{1,2}:\d{2}\b", message, re.IGNORECASE):
            return None
        time_obj = self._parse_time(message)
        return time_obj.isoformat() if time_obj else None

    async def _check_and_confirm_booking(
        self,
        conversation_id: str,
        booking_context: Dict[str, Any],
        doctor_data: List[Dict[str, Any]]
    ) -> str:
        """Check availability and prepare booking confirmation."""
        # Ensure selected_doctor_email is the source of truth
        if booking_context.get("selected_doctor_email"):
            resolved_doctor = self._find_doctor_by_email(booking_context.get("selected_doctor_email"), doctor_data)
            if resolved_doctor:
                booking_context["doctor_email"] = resolved_doctor.get("email")
                booking_context["doctor_name"] = resolved_doctor.get("name")
            else:
                return "I couldn't verify the selected doctor. Please choose a doctor again."
        elif booking_context.get("doctor_email"):
            resolved_doctor = self._find_doctor_by_email(booking_context.get("doctor_email"), doctor_data)
            if resolved_doctor:
                booking_context["selected_doctor_email"] = resolved_doctor.get("email")
                booking_context["doctor_name"] = resolved_doctor.get("name")

        if booking_context.get("doctor_name"):
            candidates = self._find_doctor_candidates_by_name(booking_context.get("doctor_name"), doctor_data)
            if booking_context.get("doctor_email") and not self._doctor_email_matches_name(booking_context, doctor_data):
                if len(candidates) == 1:
                    booking_context["selected_doctor_email"] = candidates[0].get("email")
                    booking_context["doctor_email"] = candidates[0].get("email")
                    booking_context["doctor_name"] = candidates[0].get("name")
                else:
                    self._store_doctor_candidates(conversation_id, candidates, booking_context.get("specialization"))
                    candidate_names = [self._format_doctor_name(d.get("name")) for d in candidates[:3]]
                    return (
                        f"I found multiple doctors matching {booking_context.get('doctor_name')}: "
                        f"{', '.join(candidate_names)}. Which one would you like to book with?"
                    )
            elif not booking_context.get("doctor_email") and len(candidates) == 1:
                booking_context["selected_doctor_email"] = candidates[0].get("email")
                booking_context["doctor_email"] = candidates[0].get("email")
                booking_context["doctor_name"] = candidates[0].get("name")

        # Persist selected doctor if resolved
        if booking_context.get("selected_doctor_email"):
            self.conversation_manager.update_booking_context(
                conversation_id,
                {
                    "selected_doctor_email": booking_context.get("selected_doctor_email"),
                    "doctor_email": booking_context.get("doctor_email"),
                    "doctor_name": booking_context.get("doctor_name")
                }
            )

        # Resolve doctor if needed
        doctor_email = booking_context.get("selected_doctor_email") or booking_context.get("doctor_email")
        if not doctor_email:
            if booking_context.get("doctor_name"):
                resolved_doctor = self._find_doctor_by_name(booking_context.get("doctor_name"), doctor_data)
                if not resolved_doctor:
                    return f"I couldn't find a doctor named {booking_context.get('doctor_name')}. Please choose another doctor."
                booking_context["doctor_name"] = resolved_doctor.get("name")
                booking_context["doctor_email"] = resolved_doctor.get("email")
            elif booking_context.get("specialization"):
                matching_doctors = [
                    d for d in doctor_data
                    if self._match_specialization(d.get("specialization", ""), booking_context.get("specialization"))
                ]
                if not matching_doctors:
                    return f"I couldn't find any doctors for {booking_context.get('specialization')}."
                if len(matching_doctors) > 1:
                    self._store_doctor_candidates(conversation_id, matching_doctors, booking_context.get("specialization"))
                    candidate_names = [self._format_doctor_name(d.get("name")) for d in matching_doctors[:3]]
                    return (
                        f"For {booking_context.get('specialization')}, I found multiple doctors: "
                        f"{', '.join(candidate_names)}. Which one would you like?"
                    )
                resolved_doctor = matching_doctors[0]
                booking_context["doctor_name"] = resolved_doctor.get("name")
                booking_context["doctor_email"] = resolved_doctor.get("email")

            doctor_email = booking_context.get("doctor_email")
            if doctor_email:
                self.conversation_manager.update_booking_context(
                    conversation_id,
                    {"doctor_email": doctor_email, "doctor_name": booking_context.get("doctor_name")}
                )
                self.conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    context={
                        "last_doctor_name": booking_context.get("doctor_name"),
                        "last_doctor_email": doctor_email
                    }
                )

        if not booking_context.get("doctor_email"):
            return "I couldn't determine the doctor. Please specify a doctor or specialization."

        # Check availability before confirming
        doctor_email_to_check = booking_context.get("doctor_email")
        date_to_check = self._parse_date(booking_context.get("date"))
        time_to_check = self._parse_time(booking_context.get("time"))

        # Get doctor info for working hours validation
        doctor_info = None
        if doctor_email_to_check:
            doctor_info = self._find_doctor_by_email(doctor_email_to_check, doctor_data)

        # Validate working hours BEFORE proceeding
        if time_to_check and doctor_info:
            is_within_hours, work_start, work_end = self._is_within_working_hours(time_to_check, doctor_info)
            if not is_within_hours:
                time_display = self._format_time_display(time_to_check)
                # Format working hours nicely
                work_start_formatted = self._format_slot_time(work_start) if work_start else "N/A"
                work_end_formatted = self._format_slot_time(work_end) if work_end else "N/A"
                return (
                    f"I'm sorry, {self._format_doctor_name(booking_context.get('doctor_name'))} is not available at "
                    f"{time_display}. The doctor's working hours are {work_start_formatted} to {work_end_formatted}. "
                    f"Please choose a time within these hours."
                )

        if doctor_email_to_check and date_to_check and time_to_check:
            try:
                async with CalendarClient() as calendar_client:
                    availability = await calendar_client.get_doctor_availability(doctor_email_to_check, date_to_check)
                    available_slots = availability.get("available_slots", [])

                    # Check if requested time is in available slots
                    requested_time_str = time_to_check.strftime("%H:%M")
                    # Also try with seconds for comparison
                    requested_time_full = time_to_check.strftime("%H:%M:%S")

                    # Log for debugging
                    logger.info(f"Checking availability: requested={requested_time_full}, available_slots={[s.get('start_time') for s in available_slots[:3]]}")

                    is_available = any(
                        slot.get("start_time") in [requested_time_str, requested_time_full] or
                        slot.get("start_time", "").startswith(requested_time_str)
                        for slot in available_slots
                    )

                    logger.info(f"Availability check result: {is_available}")

                    if not is_available and available_slots:
                        # Format available times nicely (12-hour format, grouped by time of day)
                        time_display = self._format_time_display(time_to_check)
                        date_display = self._format_date_display(booking_context.get('date'))
                        slots_text = self._format_slots(available_slots, target_date=date_to_check)
                        return (
                            f"I'm sorry, {self._format_doctor_name(booking_context.get('doctor_name'))} is not available at "
                            f"{time_display} on {date_display}.\n\n"
                            f"Available slots:\n{slots_text}\n\nWhich time would you prefer?"
                        )
                    elif not available_slots:
                        return (
                            f"{self._format_doctor_name(booking_context.get('doctor_name'))} has no availability on "
                            f"{booking_context.get('date')}. Would you like to try a different date?"
                        )
            except Exception as e:
                logger.warning(f"Couldn't check availability: {e}")
                # Continue with booking if availability check fails

        # Prepare confirmation with better formatting
        self.conversation_manager.update_conversation(
            conversation_id=conversation_id,
            state=ConversationState.CONFIRMING_BOOKING,
            context={"pending_action": "book"}
        )

        doctor_display = self._format_doctor_name(booking_context.get('doctor_name'))
        specialization = booking_context.get('specialization', 'specialist')
        patient_name = self._format_patient_name(booking_context.get('patient_name'))
        date_display = self._format_date_display(booking_context.get('date'))
        # Show parsed time in 12-hour format for clarity
        time_display = self._format_time_display(time_to_check) if time_to_check else booking_context.get('time')

        return (
            f"Please confirm your appointment details:\n\n"
            f"  Date: {date_display}\n"
            f"  Time: {time_display}\n"
            f"  Doctor: {doctor_display} ({specialization})\n"
            f"  Patient: {patient_name}\n"
            f"  Phone: {booking_context.get('patient_phone')}\n\n"
            f"Reply 'yes' to confirm or 'no' to cancel."
        )

    def _format_patient_name(self, name: Optional[str]) -> str:
        """Format patient name with proper capitalization."""
        if not name:
            return "N/A"
        return name.title()

    def _format_date_display(self, date_str: Optional[str]) -> str:
        """Format date string for display."""
        if not date_str:
            return "N/A"
        try:
            # Try to parse and format nicely
            parsed = date_parser.parse(date_str, fuzzy=True)
            return parsed.strftime("%B %d, %Y")  # e.g., "February 03, 2025"
        except Exception:
            return date_str  # Return as-is if parsing fails

    def _generate_cancellation_alternatives(self, booking_context: Optional[Any]) -> str:
        """Generate helpful alternatives when user cancels a booking."""
        if not booking_context:
            return "No problem. Would you like to book a different appointment or get information about our doctors?"

        alternatives = []
        doctor_name = None
        if hasattr(booking_context, 'doctor_name'):
            doctor_name = booking_context.doctor_name
        elif isinstance(booking_context, dict):
            doctor_name = booking_context.get('doctor_name')

        if doctor_name:
            alternatives.append(f"choose a different time with {self._format_doctor_name(doctor_name)}")
            alternatives.append("select a different doctor")
        else:
            alternatives.append("try a different date or time")
            alternatives.append("see other available doctors")

        return f"No problem, I've cancelled that booking. Would you like to {alternatives[0]}, or {alternatives[1]}?"

    def _needs_doctor_data(self, intent: IntentType, message: str = "") -> bool:
        """Determine whether doctor data is required for an intent."""
        # Always need doctor data for these intents
        if intent in {
            IntentType.BOOK_APPOINTMENT,
            IntentType.GET_DOCTOR_INFO,
            IntentType.CHECK_AVAILABILITY
        }:
            return True

        # Also fetch doctor data when symptoms or health issues are mentioned
        # This prevents "no doctors available" responses when user describes symptoms
        if message and self._message_contains_symptoms(message):
            return True

        return False

    def _message_contains_symptoms(self, message: str) -> bool:
        """Check if message contains symptoms or health-related terms."""
        symptom_keywords = [
            "allergy", "allergies", "rash", "itching", "itch", "pain", "ache",
            "fever", "cough", "cold", "headache", "stomach", "skin", "issue",
            "problem", "sick", "unwell", "ill", "burning", "swelling", "infection",
            "irritation", "discomfort", "hurt", "hurting", "sore", "throat",
            "breathing", "chest", "heart", "dizzy", "nausea", "vomiting",
            "diarrhea", "constipation", "fatigue", "tired", "weakness",
            "treatment", "checkup", "check-up", "consultation", "condition"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in symptom_keywords)

    def _get_doctor_pronoun(self, name: Optional[str]) -> str:
        """Get appropriate pronoun based on doctor's name.

        Uses simple heuristics based on common Indian names.
        Returns 'she' for likely female names, 'he' for likely male names,
        'they' if uncertain.
        """
        if not name:
            return "they"

        first_name = name.replace("Dr.", "").replace("Dr", "").strip().split()[0].lower()

        # Common Indian female name endings and names
        female_indicators = [
            "aditi", "priya", "neha", "pooja", "anjali", "swati", "kavita",
            "sunita", "anita", "rita", "meena", "seema", "rekha", "suman",
            "nisha", "asha", "usha", "lata", "geeta", "sita", "radha",
            "deepa", "shobha", "sarita", "mamta", "kamla", "indira",
            "lakshmi", "durga", "parvati", "savita", "saroj", "kusum",
            "maya", "renu", "manju", "sudha", "pushpa", "shanti", "kiran",
            "sangeeta", "babita", "archana", "vandana", "sapna", "divya",
            "sneha", "shruti", "megha", "kriti", "aishwarya", "shreya",
            "tanvi", "ishita", "nikita", "riya", "tanya", "sonia", "monica",
            "preeti", "mansi", "jyoti", "pallavi", "aparna", "bhavna"
        ]

        # Check if name ends with common female suffixes
        female_suffixes = ["ita", "ika", "ini", "ati", "ali", "eeta", "itha"]

        if first_name in female_indicators:
            return "she"

        for suffix in female_suffixes:
            if first_name.endswith(suffix):
                return "she"

        # Common male names
        male_indicators = [
            "amit", "rahul", "vikram", "raj", "suresh", "rajesh", "mahesh",
            "ramesh", "anil", "sunil", "vijay", "ajay", "sanjay", "rakesh",
            "prakash", "dinesh", "naresh", "girish", "satish", "ashok",
            "manoj", "vinod", "arvind", "ravi", "kumar", "arun", "varun",
            "karan", "rohan", "mohit", "nikhil", "sahil", "vishal", "kapil"
        ]

        if first_name in male_indicators:
            return "he"

        # Default to 'they' if uncertain
        return "they"

    def _is_yes_no_question_about_doctor(self, message: str) -> bool:
        """Check if the message is a yes/no question about doctor availability."""
        message_lower = message.lower()
        # Patterns indicating yes/no questions about doctor availability
        yes_no_patterns = [
            r"\bis\b.*\b(from|in|part of|available|your)\b.*\b(network|clinic|hospital)\b",
            r"\bdo you have\b",
            r"\bis\b.*\bavailable\b",
            r"\bcan i (see|book|meet)\b",
            r"\bfrom your (network|clinic)\b"
        ]
        return any(re.search(pattern, message_lower) for pattern in yes_no_patterns)

    def _wants_more_information(self, message: str) -> bool:
        """Check if user wants more information about a previously mentioned doctor/topic."""
        message_lower = message.lower().strip()

        # Direct phrases indicating want for more info
        more_info_phrases = [
            "tell me more",
            "more info",
            "more information",
            "more details",
            "tell me about",
            "more about",
            "details",
            "know more",
            "learn more",
            "elaborate",
            "explain more",
            "what else",
            "anything else about",
        ]

        for phrase in more_info_phrases:
            if phrase in message_lower:
                return True

        # Short follow-up patterns
        short_patterns = [
            r"^(tell me|show me|give me)(\s+more)?$",
            r"^more$",
            r"^details?$",
            r"^info(rmation)?$",
        ]

        for pattern in short_patterns:
            if re.match(pattern, message_lower):
                return True

        return False

    def _wants_info_about_all(self, message: str) -> bool:
        """Check if user wants information about ALL/BOTH doctors."""
        message_lower = message.lower().strip()

        # Phrases indicating user wants info about multiple doctors
        all_info_phrases = [
            "both doctor",
            "both of them",
            "tell me about both",
            "tell me about them",
            "tell me both",
            "info about both",
            "info on both",
            "about them",
            "about all",
            "all doctor",
            "all of them",
            "each doctor",
            "each of them",
            "everyone",
            "all the doctor",
        ]

        for phrase in all_info_phrases:
            if phrase in message_lower:
                return True

        # Pattern for "tell me more about them/both"
        if re.search(r"\b(tell|show|give)\s+(me\s+)?(more\s+)?(about\s+)?(them|both|all)\b", message_lower):
            return True

        return False

    def _format_multiple_doctors_info(
        self,
        candidate_names: List[str],
        doctor_data: List[Dict[str, Any]],
        conversation_id: str
    ) -> str:
        """Format information about multiple doctors."""
        doctor_infos = []

        for name in candidate_names[:3]:  # Limit to 3 doctors
            doctor = self._find_doctor_by_name(name, doctor_data)
            if doctor:
                display_name = self._format_doctor_name(doctor.get("name"))
                languages = self._safe_list(doctor.get("languages"))
                working_hours = doctor.get("working_hours") or {}
                exp_years = doctor.get("experience_years", "several")

                info = (
                    f"{display_name}: {exp_years} years experience, "
                    f"speaks {', '.join(languages) if languages else 'multiple languages'}, "
                    f"available {working_hours.get('start', 'N/A')} to {working_hours.get('end', 'N/A')}"
                )
                doctor_infos.append(info)

        if doctor_infos:
            # Update context with last specialization
            if candidate_names:
                first_doc = self._find_doctor_by_name(candidate_names[0], doctor_data)
                if first_doc:
                    self.conversation_manager.update_conversation(
                        conversation_id=conversation_id,
                        context={
                            "last_specialization": first_doc.get("specialization"),
                            "awaiting_doctor_info": True
                        }
                    )

            return "Here's information about our doctors:\n\n" + "\n\n".join(doctor_infos) + "\n\nWould you like to book an appointment with any of them?"

        return "I couldn't find detailed information for these doctors."

    def _apply_rule_based_intent(
        self,
        message: str,
        intent_classification: IntentClassification
    ) -> IntentClassification:
        """Fallback intent detection using simple keyword rules."""
        text = message.strip().lower()

        if intent_classification.intent == IntentType.RESCHEDULE_APPOINTMENT:
            has_appointment_id = self._extract_appointment_id(message)
            wants_booking = re.search(r"\b(book|schedule)\b", text)
            wants_reschedule = re.search(r"\b(reschedule|change|move)\b", text)
            if not has_appointment_id and wants_booking and not wants_reschedule:
                return IntentClassification(
                    intent=IntentType.BOOK_APPOINTMENT,
                    confidence=max(intent_classification.confidence, 0.7),
                    entities=intent_classification.entities
                )

        rules = [
            (r"\b(book|schedule|appointment)\b", IntentType.BOOK_APPOINTMENT),
            (r"\b(reschedule|change|move)\b", IntentType.RESCHEDULE_APPOINTMENT),
            (r"\b(cancel|delete)\b", IntentType.CANCEL_APPOINTMENT),
            (r"\b(availability|available|slots)\b", IntentType.CHECK_AVAILABILITY),
            (r"\b(doctor|specialist|specialization|information)\b", IntentType.GET_DOCTOR_INFO),
            (r"\b(my appointments?|appointments list|appointment id)\b", IntentType.GET_MY_APPOINTMENTS),
            # Health symptoms should trigger doctor lookup
            (r"\b(allergy|allergies|rash|skin\s+problem|skin\s+issue|itching)\b", IntentType.GET_DOCTOR_INFO),
            (r"\b(fever|cough|cold|headache|pain|ache|sick|unwell)\b", IntentType.GET_DOCTOR_INFO),
            (r"\b(treatment|checkup|check-up|consultation)\b", IntentType.GET_DOCTOR_INFO),
        ]

        if intent_classification.intent != IntentType.UNKNOWN and intent_classification.confidence >= 0.5:
            return intent_classification

        for pattern, intent in rules:
            if re.search(pattern, text):
                return IntentClassification(
                    intent=intent,
                    confidence=max(intent_classification.confidence, 0.65),
                    entities=intent_classification.entities
                )

        return intent_classification

    async def _get_doctor_data(self) -> List[Dict[str, Any]]:
        """Fetch doctor data with Redis caching."""
        if self._redis:
            cached = self._redis.get(self._doctor_cache_key)
            if cached:
                try:
                    doctors = json.loads(cached)
                    if isinstance(doctors, list):
                        return doctors
                except Exception:
                    pass
        try:
            async with CalendarClient() as calendar_client:
                doctor_response = await calendar_client.get_doctor_data()

            if not isinstance(doctor_response, dict):
                logger.warning("Doctor data response was not a dict.")
                doctors = []
            else:
                doctors = doctor_response.get("doctors", [])
                if doctor_response.get("error"):
                    logger.warning(f"Doctor data fetch failed: {doctor_response.get('error')}")

            if not isinstance(doctors, list):
                logger.warning("Doctor data was not a list. Falling back to empty list.")
                doctors = []
            else:
                doctors = [d for d in doctors if isinstance(d, dict)]

            if doctors and self._redis:
                try:
                    self._redis.setex(
                        self._doctor_cache_key,
                        self._doctor_cache_ttl_seconds,
                        json.dumps(doctors)
                    )
                except Exception as e:
                    logger.warning(f"Failed to cache doctor data in Redis: {e}")
            return doctors
        except Exception as e:
            logger.error(f"Failed to fetch doctor data: {e}")
            return []

    def _extract_appointment_id(self, message: str) -> Optional[str]:
        """Extract appointment ID (UUID) from message."""
        match = re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", message)
        return match.group(0) if match else None

    def _is_affirmative(self, message: str) -> bool:
        """Check if a message is an affirmative response."""
        normalized = message.strip().lower()

        # Direct affirmative words
        if re.search(r"\b(yes|y|yep|yeah|yup|ya|yah|sure|confirm|ok|okay|please do|go ahead|proceed|do it|book it|done|fine|alright|absolutely|definitely)\b", normalized):
            return True

        # Phrases that indicate confirmation
        affirmative_phrases = [
            "book now", "ok book", "please book", "go ahead", "let's do it",
            "sounds good", "that works", "perfect", "great", "do it"
        ]
        for phrase in affirmative_phrases:
            if phrase in normalized:
                return True

        # Handle typos like "yop" for "yup"
        if re.search(r"\b(yop|yos|yas|yse)\b", normalized):
            return True

        return False

    def _is_negative(self, message: str) -> bool:
        """Check if a message is a negative response."""
        normalized = message.strip().lower()
        return bool(re.search(r"\b(no|n|cancel|stop|not now|don't|do not)\b", normalized))

    def _is_clarifying_question(self, message: str) -> bool:
        """Check if a message is a clarifying question rather than a confirmation."""
        normalized = message.strip().lower()

        # Check for question marks or question words
        is_question = (
            "?" in message or
            re.search(r"^\s*(is|are|can|could|what|when|how|which|do|does|will|would)\b", normalized)
        )

        # Check for availability/slot related questions
        availability_keywords = [
            "slot", "timing", "available", "availability", "other time", "more time",
            "upto", "until", "only", "last slot", "any other", "different time"
        ]
        asks_about_availability = any(kw in normalized for kw in availability_keywords)

        # A clarifying question is NOT a simple yes/no and asks about slots or is phrased as a question
        is_not_confirmation = not self._is_affirmative(message) and not self._is_negative(message)

        return is_not_confirmation and (is_question or asks_about_availability)

    def _is_timing_constraint_question(self, message: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user is asking about timing constraints (e.g., why no evening slots).

        Returns:
            Tuple of (is_timing_question, time_period_asked)
        """
        normalized = message.strip().lower()

        # Time period keywords
        time_periods = {
            "evening": "evening",
            "late evening": "evening",
            "early evening": "evening",
            "afternoon": "afternoon",
            "late afternoon": "afternoon",
            "early afternoon": "afternoon",
            "morning": "morning",
            "early morning": "morning",
            "late morning": "morning",
            "night": "evening",
        }

        # Patterns that indicate asking about timing constraints
        constraint_patterns = [
            r"\b(is|are)\s+(he|she|they|doctor)\s+(not\s+)?available\s+.*?(evening|afternoon|morning|night)",
            r"\b(not|no)\s+available\s+.*?(evening|afternoon|morning|night)",
            r"\b(why|how come)\s+.*?(only|no)\s+.*?(evening|afternoon|morning)",
            r"\bonly\s+(morning|afternoon|evening)\s+slot",
            r"\b(evening|afternoon|morning|night)\s+(timing|slot|time)",
            r"\b(available|free)\s+in\s+(the\s+)?(evening|afternoon|morning)",
        ]

        for pattern in constraint_patterns:
            match = re.search(pattern, normalized)
            if match:
                # Find which time period they're asking about
                for period_key, period_value in time_periods.items():
                    if period_key in normalized:
                        return True, period_value
                return True, None

        # Simple check - are they asking about a time period?
        for period_key, period_value in time_periods.items():
            if period_key in normalized and any(word in normalized for word in ["available", "timing", "slot", "time"]):
                return True, period_value

        return False, None

    def _normalize_specialization(self, value: Optional[str]) -> Optional[str]:
        """Normalize specialization terms (e.g., cardiologist -> cardiology)."""
        if not value:
            return None

        normalized = value.strip().lower()
        synonyms = self._specialization_synonyms()
        return synonyms.get(normalized, normalized)

    def _specialization_synonyms(self) -> Dict[str, str]:
        """Synonyms and common misspellings for specializations."""
        return {
            "cardiologist": "cardiology",
            "dermatologist": "dermatology",
            "dermatalogist": "dermatology",
            "dermatoligist": "dermatology",
            "dermatolgy": "dermatology",
            "neurologist": "neurology",
            "gynecologist": "gynecology",
            "gynaecologist": "gynecology",
            "pediatrician": "pediatrics",
            "paediatrician": "pediatrics",
            "orthopedist": "orthopedics",
            "orthopaedist": "orthopedics",
            "ophthalmologist": "ophthalmology",
            "ent": "otolaryngology"
        }

    def _symptom_to_specialization(self) -> Dict[str, str]:
        """Map common symptoms to appropriate specialization."""
        return {
            # Dermatology symptoms
            "rash": "dermatology",
            "skin": "dermatology",
            "acne": "dermatology",
            "pimple": "dermatology",
            "itching": "dermatology",
            "itch": "dermatology",
            "allergy": "dermatology",
            "eczema": "dermatology",
            "psoriasis": "dermatology",
            "hair loss": "dermatology",
            "dandruff": "dermatology",

            # Cardiology symptoms
            "heart": "cardiology",
            "chest pain": "cardiology",
            "palpitation": "cardiology",
            "blood pressure": "cardiology",
            "bp": "cardiology",
            "hypertension": "cardiology",

            # Orthopedics symptoms
            "bone": "orthopedics",
            "joint": "orthopedics",
            "knee": "orthopedics",
            "back pain": "orthopedics",
            "spine": "orthopedics",
            "fracture": "orthopedics",
            "arthritis": "orthopedics",
            "muscle pain": "orthopedics",

            # Gynecology symptoms
            "pregnancy": "gynecology",
            "menstrual": "gynecology",
            "period": "gynecology",
            "women health": "gynecology",
            "ovary": "gynecology",
            "uterus": "gynecology",

            # Pediatrics symptoms
            "child": "pediatrics",
            "baby": "pediatrics",
            "infant": "pediatrics",
            "kid": "pediatrics",
            "vaccination": "pediatrics",

            # General medicine symptoms
            "fever": "general medicine",
            "cold": "general medicine",
            "cough": "general medicine",
            "flu": "general medicine",
            "headache": "general medicine",
            "fatigue": "general medicine",
            "weakness": "general medicine",
            "diabetes": "general medicine",
            "thyroid": "general medicine",
        }

    def _guess_specialization_from_text(
        self,
        message: str,
        doctor_data: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Infer specialization from free text, symptoms, or fuzzy matching."""
        if not message:
            return None

        text = message.lower()

        # First check for symptom keywords - this handles "rash", "skin issue", etc.
        symptom_mapping = self._symptom_to_specialization()
        for symptom, spec in symptom_mapping.items():
            if symptom in text:
                logger.info(f"Detected symptom '{symptom}' -> suggesting '{spec}'")
                return spec

        # Then check for specialization synonyms (cardiologist -> cardiology)
        synonyms = self._specialization_synonyms()
        for key, value in synonyms.items():
            if key in text:
                return value

        # Check for direct specialization mentions
        known_specializations = {
            str(d.get("specialization")).lower()
            for d in doctor_data
            if isinstance(d, dict) and d.get("specialization")
        }

        for spec in known_specializations:
            if spec and spec in text:
                return self._normalize_specialization(spec)

        # Fuzzy matching as last resort
        tokens = re.findall(r"[a-zA-Z]+", text)
        candidates = set(known_specializations) | set(synonyms.keys()) | set(synonyms.values())
        for token in tokens:
            matches = get_close_matches(token, candidates, n=1, cutoff=0.8)
            if matches:
                return self._normalize_specialization(matches[0])

        return None

    def _match_specialization(self, doctor_specialization: str, requested_specialization: Optional[str]) -> bool:
        """Match requested specialization against doctor specialization."""
        if not requested_specialization:
            return False

        doctor_norm = self._normalize_specialization(doctor_specialization) or ""
        requested_norm = self._normalize_specialization(requested_specialization) or ""
        return requested_norm in doctor_norm or doctor_norm in requested_norm

    def _mentions_doctor_pronoun(self, message: str) -> bool:
        """Check if message refers to a doctor pronoun or reference."""
        if not message:
            return False
        lowered = message.lower()
        references = [
            "him",
            "her",
            "them",
            "that doctor",
            "that one",
            "the doctor",
            "this doctor"
        ]
        return any(ref in lowered for ref in references)

    def _match_doctor_name_in_message(
        self,
        message: str,
        doctor_data: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Find a doctor name mentioned in the message."""
        if not message:
            return None
        normalized_message = self._normalize_match_text(message)
        for doctor in doctor_data:
            name = doctor.get("name")
            if name and self._normalize_doctor_name(name) in normalized_message:
                return name
        return None

    def _find_doctor_by_name(
        self,
        doctor_name: str,
        doctor_data: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Locate a doctor dict by name."""
        normalized_target = self._normalize_doctor_name(doctor_name)
        for doctor in doctor_data:
            normalized_candidate = self._normalize_doctor_name(doctor.get("name"))
            if normalized_target and (
                normalized_target in normalized_candidate or normalized_candidate in normalized_target
            ):
                return doctor
        return None

    def _find_doctor_by_email(
        self,
        doctor_email: Optional[str],
        doctor_data: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Locate a doctor dict by email."""
        if not doctor_email:
            return None
        for doctor in doctor_data:
            if doctor.get("email") == doctor_email:
                return doctor
        return None

    def _find_doctor_candidates_by_name(
        self,
        doctor_name: Optional[str],
        doctor_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find possible doctor matches by name."""
        if not doctor_name:
            return []
        normalized_target = self._normalize_doctor_name(doctor_name)
        target_tokens = self._name_tokens(doctor_name)
        candidates = []
        for doctor in doctor_data:
            name = doctor.get("name")
            if not name:
                continue
            normalized_candidate = self._normalize_doctor_name(name)
            candidate_tokens = self._name_tokens(name)
            if (
                normalized_target in normalized_candidate
                or normalized_candidate in normalized_target
                or (target_tokens and candidate_tokens and target_tokens.intersection(candidate_tokens))
            ):
                candidates.append(doctor)
        return candidates

    def _doctor_email_matches_name(
        self,
        booking_context: Dict[str, Any],
        doctor_data: List[Dict[str, Any]]
    ) -> bool:
        """Check whether doctor_email and doctor_name refer to the same doctor."""
        doctor_email = booking_context.get("doctor_email")
        doctor_name = booking_context.get("doctor_name")
        if not doctor_email or not doctor_name:
            return False
        doctor = self._find_doctor_by_email(doctor_email, doctor_data)
        if not doctor:
            return False
        return self._names_match(doctor_name, doctor.get("name"))

    def _resolve_doctor_from_context(
        self,
        message: str,
        context: Dict[str, Any],
        doctor_data: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Resolve doctor selection from conversation context."""
        candidates = context.get("doctor_info_candidates") or []
        if not candidates:
            return None

        lowered = message.lower()

        for name in candidates:
            if name and name.lower() in lowered:
                return self._find_doctor_by_name(name, doctor_data)

        ordinal_map = {
            "first": 0,
            "1st": 0,
            "second": 1,
            "2nd": 1,
            "third": 2,
            "3rd": 2
        }
        for key, idx in ordinal_map.items():
            if key in lowered and idx < len(candidates):
                return self._find_doctor_by_name(candidates[idx], doctor_data)

        message_tokens = self._name_tokens(message)
        if message_tokens:
            for name in candidates:
                candidate_tokens = self._name_tokens(name)
                if candidate_tokens and message_tokens.intersection(candidate_tokens):
                    return self._find_doctor_by_name(name, doctor_data)

        if (self._is_affirmative(message) or self._mentions_doctor_pronoun(message)) and len(candidates) == 1:
            return self._find_doctor_by_name(candidates[0], doctor_data)

        return None

    def _store_doctor_candidates(
        self,
        conversation_id: str,
        doctors: List[Dict[str, Any]],
        specialization: Optional[str]
    ) -> None:
        """Store doctor candidates for follow-up selection."""
        names = [d.get("name") for d in doctors if d.get("name")]
        context = {
            "doctor_info_candidates": names,
            "awaiting_doctor_info": True
        }
        if specialization:
            context["last_specialization"] = specialization
        if len(names) == 1:
            context["last_doctor_name"] = names[0]
            context["last_doctor_email"] = doctors[0].get("email") if doctors else None
        self.conversation_manager.update_conversation(
            conversation_id=conversation_id,
            context=context
        )

    def _get_unique_specializations(self, doctor_data: List[Dict[str, Any]]) -> List[str]:
        """Get unique list of specializations."""
        specializations = {
            d.get("specialization") for d in doctor_data
            if isinstance(d, dict) and d.get("specialization")
        }
        return sorted(specializations)

    def _format_slot_time(self, time_str: str) -> str:
        """Format a time string (HH:MM:SS or HH:MM) to 12-hour format."""
        if not time_str:
            return ""
        try:
            # Remove seconds if present
            time_parts = time_str.split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0

            # Convert to 12-hour format
            period = "AM" if hour < 12 else "PM"
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12

            if minute == 0:
                return f"{display_hour} {period}"
            else:
                return f"{display_hour}:{minute:02d} {period}"
        except (ValueError, IndexError):
            return time_str  # Return original if parsing fails

    def _format_slots(self, slots: List[Dict[str, Any]], show_range: bool = True, target_date: Optional[date] = None) -> str:
        """Format availability slots for display, grouped by time of day.

        Args:
            slots: List of slot dictionaries with start_time
            show_range: If True, show a summary range for many slots
            target_date: If provided and is today, filter out past slots

        Returns:
            Formatted string of available times grouped by Morning/Afternoon/Evening
        """
        if not slots:
            return "No slots available"

        # Get current time for filtering past slots (IST)
        now = datetime.now(IST)
        is_today = target_date == now.date() if target_date else False

        # Get all slot times, filtering past slots if today
        all_times = []
        for slot in slots:
            start = slot.get("start_time")
            if start:
                # Filter out past slots for today
                if is_today:
                    try:
                        slot_hour = int(start.split(":")[0])
                        slot_minute = int(start.split(":")[1]) if len(start.split(":")) > 1 else 0
                        if slot_hour < now.hour or (slot_hour == now.hour and slot_minute <= now.minute):
                            continue  # Skip past slots
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Failed to parse slot time '{start}': {e}")
                        pass
                all_times.append(start)

        if not all_times:
            if is_today:
                return "No more slots available today (all remaining slots have passed)"
            return "No slots available"

        # Group by time of day: Morning (before 12), Afternoon (12-17), Evening (17+)
        morning_slots = []
        afternoon_slots = []
        evening_slots = []

        for t in all_times:
            try:
                hour = int(t.split(":")[0])
                if hour < 12:
                    morning_slots.append(t)
                elif hour < 17:
                    afternoon_slots.append(t)
                else:
                    evening_slots.append(t)
            except (ValueError, IndexError) as e:
                logger.debug(f"Failed to categorize slot time '{t}': {e}")
                pass

        # Build grouped output
        parts = []

        if morning_slots:
            morning_formatted = [self._format_slot_time(t) for t in morning_slots]
            if len(morning_slots) <= 4:
                parts.append(f"🌅 Morning: {', '.join(morning_formatted)}")
            else:
                parts.append(f"🌅 Morning: {morning_formatted[0]} - {morning_formatted[-1]} ({len(morning_slots)} slots)")

        if afternoon_slots:
            afternoon_formatted = [self._format_slot_time(t) for t in afternoon_slots]
            if len(afternoon_slots) <= 4:
                parts.append(f"☀️ Afternoon: {', '.join(afternoon_formatted)}")
            else:
                parts.append(f"☀️ Afternoon: {afternoon_formatted[0]} - {afternoon_formatted[-1]} ({len(afternoon_slots)} slots)")

        if evening_slots:
            evening_formatted = [self._format_slot_time(t) for t in evening_slots]
            if len(evening_slots) <= 4:
                parts.append(f"🌙 Evening: {', '.join(evening_formatted)}")
            else:
                parts.append(f"🌙 Evening: {evening_formatted[0]} - {evening_formatted[-1]} ({len(evening_slots)} slots)")

        if parts:
            return " | ".join(parts)

        # Fallback: show individual times
        formatted = [self._format_slot_time(t) for t in all_times[:10]]
        result = ", ".join(formatted)
        if len(all_times) > 10:
            result += f" (and {len(all_times) - 10} more)"

        return result

    def _safe_list(self, value: Any) -> List[str]:
        """Ensure value is a list of strings."""
        if isinstance(value, list):
            return [str(item) for item in value if item is not None]
        return []

    def _format_doctor_name(self, name: Optional[str]) -> str:
        """Format doctor name without duplicating prefix."""
        if not name:
            return "Dr. Unknown"
        stripped = name.strip()
        return stripped if stripped.lower().startswith("dr.") else f"Dr. {stripped}"

    def _normalize_match_text(self, value: Optional[str]) -> str:
        """Normalize text for name matching."""
        if not value:
            return ""
        lowered = value.lower()
        lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    def _normalize_doctor_name(self, name: Optional[str]) -> str:
        """Normalize doctor names by removing titles and punctuation."""
        normalized = self._normalize_match_text(name)
        normalized = re.sub(r"^dr\s+", "", normalized)
        normalized = re.sub(r"^doctor\s+", "", normalized)
        return normalized.strip()

    def _name_tokens(self, value: Optional[str]) -> set:
        """Get meaningful tokens for name matching."""
        tokens = self._normalize_match_text(value).split()
        return {t for t in tokens if t not in {"dr", "doctor"} and len(t) > 2}

    def _names_match(self, left: Optional[str], right: Optional[str]) -> bool:
        """Compare doctor names with normalization."""
        if not left or not right:
            return False
        left_norm = self._normalize_doctor_name(left)
        right_norm = self._normalize_doctor_name(right)
        if not left_norm or not right_norm:
            return False
        return left_norm in right_norm or right_norm in left_norm

    def _extract_date_from_message(self, message: str) -> Optional[str]:
        """Extract date keywords from a message more intelligently.

        This handles cases like "today any availability?" where the date
        is embedded in a longer question.
        """
        if not message:
            return None

        text = message.lower()

        # Check for today/tomorrow keywords first
        today_patterns = [
            r"\btoday\b", r"\b2day\b", r"\btday\b", r"\btoday's\b"
        ]
        for pattern in today_patterns:
            if re.search(pattern, text):
                return "today"

        tomorrow_patterns = [
            r"\btomorrow\b", r"\btommorow\b", r"\btomorow\b", r"\btmrw\b",
            r"\btmr\b", r"\b2morrow\b", r"\btmorow\b", r"\btomrow\b"
        ]
        for pattern in tomorrow_patterns:
            if re.search(pattern, text):
                return "tomorrow"

        # Check for specific date patterns (e.g., "Feb 5", "5th February", "2026-02-05")
        date_patterns = [
            r"\b\d{4}-\d{2}-\d{2}\b",  # ISO format
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",  # MM/DD/YYYY or DD/MM/YYYY
            r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?\b",  # "Feb 5th"
            r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b",  # "5th Feb"
            r"\bnext\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            r"\bthis\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)

        # If no date found, return the full message for fuzzy parsing
        return message

    def _parse_date(self, value: Optional[str]) -> Optional[date]:
        """Parse a date string into a date object. Uses IST timezone."""
        if not value:
            return None
        try:
            normalized = value.lower().strip()
            today = datetime.now(IST).date()

            # Handle common variations and typos for "tomorrow"
            tomorrow_variants = [
                "tomorrow", "tommorow", "tomorow", "tmrw", "tmr", "2morrow",
                "tmorow", "tomrow", "tommorrow", "tomorrrow", "tmorrow", "tomarrow"
            ]
            if any(variant in normalized for variant in tomorrow_variants):
                return today + timedelta(days=1)

            # Handle "today" and variations
            today_variants = ["today", "2day", "tday", "toady", "today's"]
            if any(variant in normalized for variant in today_variants):
                return today

            # Handle "day after tomorrow"
            if "day after" in normalized or "after tomorrow" in normalized:
                return today + timedelta(days=2)

            # Handle "next week" variations
            if "next week" in normalized:
                return today + timedelta(days=7)

            # Check if year is explicitly mentioned in the input
            year_explicitly_mentioned = bool(re.search(r'\b20\d{2}\b|\b\d{4}\b', value))

            # Parse with current year as default to avoid old year defaults
            default_datetime = datetime(today.year, today.month, today.day, tzinfo=IST)
            parsed_date = date_parser.parse(value, fuzzy=True, default=default_datetime).date()

            # If parsed date is in the past and year wasn't explicitly mentioned,
            # try to adjust to current or next year
            if parsed_date < today and not year_explicitly_mentioned:
                # First try current year
                try:
                    current_year_date = date(today.year, parsed_date.month, parsed_date.day)
                    if current_year_date >= today:
                        parsed_date = current_year_date
                    else:
                        # Date already passed this year, use next year
                        parsed_date = date(today.year + 1, parsed_date.month, parsed_date.day)
                except ValueError:
                    # Handle edge cases like Feb 29 in non-leap years
                    pass

            return parsed_date
        except Exception as e:
            logger.warning(f"Failed to parse date '{value}': {e}")
            return None

    def _parse_time(self, value: Optional[str]) -> Optional[dt_time]:
        """Parse a time string into a time object."""
        if not value:
            return None
        try:
            normalized = value.lower().strip()

            # Handle common time-of-day references
            time_mappings = {
                "morning": dt_time(9, 0),
                "early morning": dt_time(7, 0),
                "late morning": dt_time(11, 0),
                "noon": dt_time(12, 0),
                "afternoon": dt_time(14, 0),
                "early afternoon": dt_time(13, 0),
                "late afternoon": dt_time(16, 0),
                "evening": dt_time(18, 0),
                "early evening": dt_time(17, 0),
                "late evening": dt_time(20, 0),
                "night": dt_time(20, 0),
            }

            for key, time_val in time_mappings.items():
                if key in normalized:
                    return time_val

            # Handle "any time" or "anytime" - default to morning
            if "any" in normalized or "anytime" in normalized:
                return dt_time(9, 0)

            return date_parser.parse(value, fuzzy=True).time()
        except Exception:
            return None

    def _is_within_working_hours(
        self,
        requested_time: dt_time,
        doctor_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if requested time is within doctor's working hours.

        Returns:
            Tuple of (is_valid, working_start, working_end)
        """
        working_hours = doctor_data.get("working_hours", {})
        if not working_hours:
            return True, None, None  # No working hours defined, assume valid

        start_str = working_hours.get("start", "09:00")
        end_str = working_hours.get("end", "17:00")

        try:
            working_start = datetime.strptime(start_str, "%H:%M").time()
            working_end = datetime.strptime(end_str, "%H:%M").time()

            is_valid = working_start <= requested_time < working_end
            return is_valid, start_str, end_str
        except Exception:
            return True, None, None  # On error, assume valid

    def _format_time_display(self, time_obj: Optional[dt_time]) -> str:
        """Format time object for display (12-hour format)."""
        if not time_obj:
            return "N/A"
        return time_obj.strftime("%I:%M %p").lstrip("0")  # e.g., "3:00 PM"

    def _resolve_doctor_email(
        self,
        booking_context: Dict[str, Any],
        doctor_data: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Resolve doctor email from doctor name or specialization."""
        doctor_name = booking_context.get("doctor_name")
        specialization = booking_context.get("specialization")

        if doctor_name:
            doctor = self._find_doctor_by_name(doctor_name, doctor_data)
            if doctor:
                booking_context["doctor_name"] = doctor.get("name")
                return doctor.get("email")

        if specialization:
            matching_doctors = [
                d for d in doctor_data
                if self._match_specialization(d.get("specialization", ""), specialization)
            ]
            if len(matching_doctors) == 1:
                booking_context["doctor_name"] = matching_doctors[0].get("name")
                return matching_doctors[0].get("email")

        return None

    async def _execute_pending_action(self, conversation_id: str) -> str:
        """Execute pending action for a confirmed request."""
        conversation = self.conversation_manager.get_conversation(conversation_id)
        if not conversation:
            return "I couldn't find your conversation. Please try again."

        pending_action = conversation.context.get("pending_action")
        if not pending_action:
            return "There's no action to confirm."

        if pending_action == "book":
            return await self._execute_booking(conversation_id)
        if pending_action == "reschedule":
            return await self._execute_reschedule(conversation_id)
        if pending_action == "cancel":
            return await self._execute_cancel(conversation_id)

        return "I couldn't determine the pending action."

    async def _execute_booking(self, conversation_id: str) -> str:
        """Execute appointment booking."""
        booking_details = self.conversation_manager.get_booking_context(conversation_id)
        conversation = self.conversation_manager.get_conversation(conversation_id)
        if not booking_details or not conversation:
            return "I couldn't find the booking details. Please try again."

        booking_context = conversation.context
        doctor_email = booking_context.get("doctor_email")
        booking_date = self._parse_date(booking_context.get("date"))
        booking_time = self._parse_time(booking_context.get("time"))

        if not doctor_email or not booking_date or not booking_time:
            return "I don't have enough details to book your appointment. Please provide the doctor, date, and time."

        if not booking_context.get("patient_phone") or not booking_context.get("patient_name"):
            return "I need your name and phone number to complete the booking."

        try:
            async with CalendarClient() as calendar_client:
                # Build payload with explicit string conversion to avoid serialization errors
                booking_payload = {
                    "doctor_email": str(doctor_email) if doctor_email else None,
                    "doctor_name": str(booking_context.get("doctor_name")) if booking_context.get("doctor_name") else None,
                    "patient_mobile_number": str(booking_context.get("patient_phone")) if booking_context.get("patient_phone") else None,
                    "patient_name": str(booking_context.get("patient_name")) if booking_context.get("patient_name") else None,
                    "patient_email": str(booking_context.get("patient_email")) if booking_context.get("patient_email") else None,
                    "date": booking_date.isoformat() if booking_date else None,
                    "start_time": booking_time.isoformat() if booking_time else None,
                    "symptoms": str(booking_context.get("symptoms")) if booking_context.get("symptoms") else None
                }
                
                # Remove None values to avoid API validation issues
                booking_payload = {k: v for k, v in booking_payload.items() if v is not None}
                
                # Log booking attempt for debugging
                logger.info(f"Attempting to book: doctor={doctor_email}, date={booking_date}, time={booking_time}, payload={booking_payload}")

                # Build idempotency key to prevent duplicate bookings on retry
                idempotency_key = self._build_idempotency_key("book", booking_payload, salt=conversation_id)
                response = await calendar_client.book_appointment(booking_payload, idempotency_key=idempotency_key)
                
                # Log response for debugging
                logger.info(f"Booking response: {response}")

            if isinstance(response, dict) and response.get("error"):
                error_msg = response.get('error', 'Unknown error')
                server_detail = response.get('detail')  # API's actual reason (e.g. "Slot is not available")
                error_details = response.get('details', '')
                logger.error(f"Booking failed for {doctor_email}: {error_msg} - {error_details}")
                
                # Prefer server's detail so user sees the real reason (400/422 body)
                user_message = "I couldn't book the appointment. "
                if server_detail:
                    user_message += str(server_detail).strip()
                    if not user_message.endswith("."):
                        user_message += ". "
                    user_message += "Please try another time or check the details."
                elif "already booked" in str(error_msg).lower() or "conflict" in str(error_msg).lower():
                    user_message += "This time slot is already taken. Please choose a different time."
                elif "not available" in str(error_msg).lower():
                    user_message += "The doctor is not available at this time. Please try another slot."
                elif "invalid" in str(error_msg).lower():
                    user_message += "There's an issue with the booking details. Please try again with different information."
                else:
                    user_message += f"Error: {error_msg}. Please try another time or check the details."
                
                self.conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    state=ConversationState.GATHERING_INFO,
                    context={"pending_action": None}
                )
                return user_message

            appointment_id = response.get("id") if isinstance(response, dict) else None

            # Update conversation state but KEEP the appointment_id for potential reschedule/cancel
            self.conversation_manager.update_conversation(
                conversation_id=conversation_id,
                state=ConversationState.COMPLETED,
                context={
                    "pending_action": None,
                    # Keep appointment_id for reschedule/cancel operations
                    "last_appointment_id": appointment_id,
                    "appointment_id": appointment_id,
                    # Keep doctor info for reschedule context
                    "last_doctor_name": booking_context.get("doctor_name"),
                    "last_doctor_email": booking_context.get("doctor_email"),
                    # Clear other booking-specific context
                    "selected_doctor_email": None,
                    "date": None,
                    "time": None,
                    "patient_name": None,
                    "patient_phone": None,
                    "patient_email": None,
                    "symptoms": None,
                    "appointment_type": None,
                    "reschedule_date": None,
                    "reschedule_time": None
                }
            )
            calendar_event_id = response.get("google_calendar_event_id") if isinstance(response, dict) else None
            if not appointment_id:
                logger.error("Booking response missing appointment id")
                return "I couldn't confirm the booking. Please try again."
            
            # Build professional confirmation message
            doctor_name = self._format_doctor_name(booking_context.get('doctor_name'))
            specialization = booking_context.get('specialization', '')
            patient_name = self._format_patient_name(booking_context.get('patient_name'))
            date_display = self._format_date_display(booking_context.get('date'))

            confirmation_msg = (
                f"Your appointment has been booked successfully.\n\n"
                f"Booking Details:\n"
                f"  - Doctor: {doctor_name}{' (' + specialization + ')' if specialization else ''}\n"
                f"  - Date: {date_display}\n"
                f"  - Time: {booking_context.get('time')}\n"
                f"  - Patient: {patient_name}\n"
                f"  - Appointment ID: {appointment_id}\n\n"
            )

            if not calendar_event_id:
                confirmation_msg += "Calendar sync is in progress and will complete shortly.\n\n"

            confirmation_msg += "You will receive a confirmation. Is there anything else I can help you with?"
            
            return confirmation_msg
        except Exception as e:
            logger.exception(f"Booking failed with exception: {e}")
            error_detail = str(e)
            user_message = "I couldn't book the appointment. "
            
            # Provide helpful error details
            if "connection" in error_detail.lower() or "timeout" in error_detail.lower():
                user_message += "There was a connection issue. Please try again in a moment."
            elif "validation" in error_detail.lower():
                user_message += "Some booking details need correction. Please verify the date, time, and doctor."
            else:
                user_message += f"Technical error occurred. Please try again or contact support."
            
            return user_message

    async def _execute_reschedule(self, conversation_id: str) -> str:
        """Execute appointment reschedule."""
        conversation = self.conversation_manager.get_conversation(conversation_id)
        if not conversation:
            return "I couldn't find your conversation. Please try again."

        appointment_id = conversation.context.get("appointment_id")
        new_date = self._parse_date(conversation.context.get("reschedule_date"))
        new_time = self._parse_time(conversation.context.get("reschedule_time"))

        if not appointment_id or not new_date or not new_time:
            return "I need the appointment ID, new date, and new time to reschedule."

        try:
            async with CalendarClient() as calendar_client:
                current = await calendar_client.get_appointment(appointment_id)
                if not current or current.get("error"):
                    return "I couldn't find that appointment. Please check the appointment ID."

                start_time_str = current.get("start_time")
                end_time_str = current.get("end_time")
                if not start_time_str or not end_time_str:
                    return "I couldn't determine the appointment duration."

                current_start = self._parse_time(start_time_str)
                current_end = self._parse_time(end_time_str)
                if not current_start or not current_end:
                    return "I couldn't determine the appointment duration."

                duration_minutes = int(
                    (datetime.combine(date.today(), current_end) - datetime.combine(date.today(), current_start)).total_seconds() / 60
                )
                new_end = (datetime.combine(date.today(), new_time) + timedelta(minutes=duration_minutes)).time()

                reschedule_payload = {
                    "new_date": new_date.isoformat(),
                    "new_start_time": new_time.isoformat(),
                    "new_end_time": new_end.isoformat()
                }
                idempotency_key = self._build_idempotency_key(
                    "reschedule",
                    {"appointment_id": appointment_id, **reschedule_payload},
                    salt=conversation_id
                )
                response = await calendar_client.reschedule_appointment(
                    appointment_id,
                    reschedule_payload,
                    idempotency_key=idempotency_key
                )

            if isinstance(response, dict) and response.get("error"):
                logger.error(f"Reschedule failed for {appointment_id}: {response.get('error')}")
                return "I couldn't reschedule the appointment because that time slot is not available. Please try a different time."

            # Clear reschedule context after successful reschedule
            self.conversation_manager.update_conversation(
                conversation_id=conversation_id,
                state=ConversationState.COMPLETED,
                context={
                    "pending_action": None,
                    "reschedule_in_progress": False,
                    "reschedule_date": None,
                    "reschedule_time": None
                }
            )
            return "Appointment rescheduled successfully!"
        except Exception as e:
            logger.error(f"Reschedule failed: {e}")
            return "I couldn't reschedule the appointment due to an error. Please try again."

    async def _execute_cancel(self, conversation_id: str) -> str:
        """Execute appointment cancellation."""
        conversation = self.conversation_manager.get_conversation(conversation_id)
        if not conversation:
            return "I couldn't find your conversation. Please try again."

        appointment_id = conversation.context.get("appointment_id")
        if not appointment_id:
            return "I need the appointment ID to cancel the appointment."

        try:
            async with CalendarClient() as calendar_client:
                idempotency_key = self._build_idempotency_key(
                    "cancel",
                    {"appointment_id": appointment_id},
                    salt=conversation_id
                )
                response = await calendar_client.cancel_appointment(appointment_id, idempotency_key=idempotency_key)

            if isinstance(response, dict) and response.get("error"):
                logger.error(f"Cancel failed for {appointment_id}: {response.get('error')}")
                return "I couldn't cancel the appointment. Please check the appointment ID and try again."

            self.conversation_manager.update_conversation(
                conversation_id=conversation_id,
                state=ConversationState.COMPLETED,
                context={"pending_action": None}
            )
            return "Appointment cancelled successfully!"
        except Exception as e:
            logger.error(f"Cancel failed: {e}")
            return "I couldn't cancel the appointment due to an error. Please try again."

    def _determine_conversation_state(self, intent: IntentType, conversation_id: str) -> ConversationState:
        """Determine the new conversation state based on intent."""
        conversation = self.conversation_manager.get_conversation(conversation_id)
        if conversation and conversation.context.get("pending_action"):
            return ConversationState.CONFIRMING_BOOKING

        if intent == IntentType.BOOK_APPOINTMENT:
            return ConversationState.GATHERING_INFO
        elif intent in [IntentType.RESCHEDULE_APPOINTMENT, IntentType.CANCEL_APPOINTMENT]:
            return ConversationState.CONFIRMING_BOOKING
        else:
            return ConversationState.INITIAL

    def _get_suggested_actions(self, intent: IntentType, conversation_id: str) -> List[str]:
        """Get suggested actions based on intent and context."""
        if intent == IntentType.BOOK_APPOINTMENT:
            return ["book_appointment", "check_availability"]
        elif intent == IntentType.GET_DOCTOR_INFO:
            return ["get_doctor_info", "check_availability"]
        else:
            return ["book_appointment", "get_doctor_info", "check_availability"]

    def _requires_confirmation(self, intent: IntentType, conversation_id: str) -> bool:
        """Check if the current state requires user confirmation."""
        conversation = self.conversation_manager.get_conversation(conversation_id)
        if not conversation:
            return False

        return conversation.state in [ConversationState.CONFIRMING_BOOKING, ConversationState.BOOKING_APPOINTMENT]
