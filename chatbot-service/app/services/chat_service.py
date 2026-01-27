"""
Main Chat Service that orchestrates LLM, calendar client, and conversation management.
"""
import logging
import re
import time as time_module
import traceback
from difflib import get_close_matches
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta, time as dt_time
from dateutil import parser as date_parser

from app.core.config import settings
from app.models.chat import (
    ChatRequest,
    ChatResponse,
    IntentType,
    ConversationState,
    MessageRole,
    BookingDetails,
    EntityType,
    IntentClassification
)
from app.services.llm_service import LLMService
from app.services.calendar_client import CalendarClient
from app.services.conversation_manager import ConversationManager

logger = logging.getLogger(__name__)


class ChatService:
    """Main service for handling chat interactions."""

    BOOKING_CONTEXT_FIELDS = (
        "appointment_id",
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
        self._doctor_cache: Dict[str, Any] = {"timestamp": 0.0, "data": []}
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
                self.conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    state=ConversationState.INITIAL,
                    context={"pending_action": None}
                )
                response_text = "Okay, I won't proceed. Let me know if you'd like to do something else."
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

            # Get doctor data only when needed
            doctor_data: List[Dict[str, Any]] = []
            if self._needs_doctor_data(intent_classification.intent):
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
            return await self._handle_my_appointments_intent(conversation_id)

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

        # Extract booking details from entities and fallback parsing
        extracted = self._extract_booking_details_from_entities(intent.entities)
        booking_context = self._merge_booking_context(booking_context, extracted)

        fallback = self._extract_booking_details_from_message(message, booking_context, context)
        booking_context = self._merge_booking_context(booking_context, fallback)

        # Resolve doctor/specialization from prior context if missing
        if not booking_context.get("doctor_name") and context.get("last_doctor_name"):
            booking_context["doctor_name"] = context.get("last_doctor_name")
        if (
            not booking_context.get("doctor_email")
            and context.get("last_doctor_email")
            and self._names_match(booking_context.get("doctor_name"), context.get("last_doctor_name"))
        ):
            booking_context["doctor_email"] = context.get("last_doctor_email")
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

        # Check what information we have and what's missing
        missing_info = self._get_missing_booking_info(booking_context)

        if missing_info:
            return self._prompt_for_missing_info(missing_info, booking_context)
        else:
            # We have all info, check availability and prepare confirmation
            return await self._check_and_confirm_booking(conversation_id, booking_context, doctor_data)

    async def _handle_reschedule_intent(self, message: str, intent: Any, conversation_id: str) -> str:
        """Handle appointment rescheduling intent."""
        appointment_id = self._extract_appointment_id(message)
        reschedule_context = {}
        if appointment_id:
            reschedule_context["appointment_id"] = appointment_id

        # Extract date/time entities for rescheduling
        reschedule_context.update(self._extract_reschedule_details(intent.entities))
        self.conversation_manager.update_booking_context(conversation_id, reschedule_context)

        missing_info = []
        if not reschedule_context.get("appointment_id"):
            missing_info.append("your appointment ID")
        if not reschedule_context.get("reschedule_date"):
            missing_info.append("the new date")
        if not reschedule_context.get("reschedule_time"):
            missing_info.append("the new time")

        if missing_info:
            return f"I can help reschedule that. I still need {', '.join(missing_info)}."

        self.conversation_manager.update_conversation(
            conversation_id=conversation_id,
            state=ConversationState.CONFIRMING_BOOKING,
            context={"pending_action": "reschedule"}
        )
        return (
            "Please confirm: I will reschedule your appointment to "
            f"{reschedule_context.get('reschedule_date')} at {reschedule_context.get('reschedule_time')}. "
            "Reply with 'yes' to proceed or 'no' to cancel."
        )

    async def _handle_cancel_intent(self, message: str, intent: Any, conversation_id: str) -> str:
        """Handle appointment cancellation intent."""
        appointment_id = self._extract_appointment_id(message)
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

        if not doctor_name:
            doctor_name = self._match_doctor_name_in_message(message, doctor_data)

        if not doctor_name:
            resolved_doctor = self._resolve_doctor_from_context(message, context, doctor_data)
            if resolved_doctor:
                doctor_name = resolved_doctor.get("name")

        if not specialization:
            specialization = self._guess_specialization_from_text(message, doctor_data)

        if not specialization and context.get("last_specialization") and self._mentions_doctor_pronoun(message):
            specialization = context.get("last_specialization")

        if not doctor_name and not specialization:
            candidates = context.get("doctor_info_candidates") or []
            if context.get("awaiting_doctor_info") and candidates:
                if self._is_affirmative(message) or self._mentions_doctor_pronoun(message):
                    candidate_names = [self._format_doctor_name(name) for name in candidates[:3]]
                    return (
                        "Which doctor would you like more information about? "
                        f"I have {', '.join(candidate_names)}."
                    )

        if doctor_name:
            # Find specific doctor
            doctor = next(
                (
                    d for d in doctor_data
                    if doctor_name.lower() in (d.get("name") or "").lower()
                ),
                None
            )
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
                return (
                    f"{display_name} is a {doctor.get('specialization', 'specialist')} "
                    f"with {doctor.get('experience_years', 'unknown')} years of experience. "
                    f"They speak {', '.join(languages) if languages else 'multiple languages'} "
                    f"and work {', '.join(working_days) if working_days else 'varied days'} "
                    f"from {working_hours.get('start', 'N/A')} to {working_hours.get('end', 'N/A')}."
                )
            else:
                self.conversation_manager.update_conversation(
                    conversation_id=conversation_id,
                    context={"awaiting_doctor_info": False}
                )
                return f"I couldn't find a doctor named {doctor_name}. Let me show you our available doctors."

        elif specialization:
            # Find doctors by specialization
            normalized_specialization = self._normalize_specialization(specialization)
            matching_doctors = [
                d for d in doctor_data
                if self._match_specialization(d.get("specialization") or "", normalized_specialization)
            ]
            if matching_doctors:
                self._store_doctor_candidates(conversation_id, matching_doctors, normalized_specialization)
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
            requested_date = message

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

                slots_text = self._format_slots(slots)
                return f"{self._format_doctor_name(doctor_name)} has availability on {date_obj.isoformat()}: {slots_text}"

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

                summaries = []
                for doctor in available_doctors[:3]:
                    slots_text = self._format_slots(doctor.get("available_slots", []))
                    summaries.append(f"{self._format_doctor_name(doctor.get('name'))}: {slots_text}")

                return f"Available {specialization} doctors on {date_obj.isoformat()}: " + " | ".join(summaries)

        return "Please tell me which doctor or specialty you'd like and the date you're looking for."

    async def _handle_my_appointments_intent(self, conversation_id: str) -> str:
        """Handle requests for user's appointments."""
        return "I'd be happy to show you your appointments. Could you please provide your patient ID or contact information so I can look up your appointments?"

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
                booking_details["patient_name"] = entity.value
            elif entity.type == EntityType.PHONE_NUMBER:
                booking_details["patient_phone"] = entity.value
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
        """Ask for the next missing piece of booking info with context."""
        if not missing_info:
            return "What details would you like to provide?"

        primary = missing_info[0]
        known_parts = []

        if booking_context.get("doctor_name"):
            known_parts.append(f"doctor: {self._format_doctor_name(booking_context.get('doctor_name'))}")
        elif booking_context.get("specialization"):
            known_parts.append(f"specialty: {booking_context.get('specialization')}")
        if booking_context.get("date"):
            known_parts.append(f"date: {booking_context.get('date')}")
        if booking_context.get("time"):
            known_parts.append(f"time: {booking_context.get('time')}")
        if booking_context.get("patient_name"):
            known_parts.append(f"name: {booking_context.get('patient_name')}")
        if booking_context.get("patient_phone"):
            known_parts.append(f"phone: {booking_context.get('patient_phone')}")

        known_text = f"I have {', '.join(known_parts)}. " if known_parts else ""

        if primary == "the doctor or specialization":
            return f"{known_text}Which doctor or specialty would you like to book?"
        if primary == "the appointment date":
            return f"{known_text}What date should I book the appointment for?"
        if primary == "the appointment time":
            return f"{known_text}What time should I book the appointment for?"
        if primary == "your name":
            return f"{known_text}May I have your name?"
        if primary == "your phone number":
            return f"{known_text}May I have your phone number?"

        return f"{known_text}Please provide {primary}."

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

        if not booking_context.get("time"):
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
        digits = re.findall(r"\d+", message)
        if not digits:
            return None
        candidate = "".join(digits)
        return candidate if len(candidate) >= 3 else None

    def _extract_name_from_text(self, message: str) -> Optional[str]:
        """Extract name from text patterns like 'my name is'."""
        match = re.search(r"\bmy name is\s+([a-zA-Z][a-zA-Z\s'.-]{1,50})", message, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r"\bi am\s+([a-zA-Z][a-zA-Z\s'.-]{1,50})", message, re.IGNORECASE)
        if match:
            if re.search(r"\b(looking for|seeking|searching)\b", message, re.IGNORECASE):
                return None
            return match.group(1).strip()
        return None

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
        # Resolve doctor if needed
        doctor_email = booking_context.get("doctor_email")
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

        # Prepare confirmation
        self.conversation_manager.update_conversation(
            conversation_id=conversation_id,
            state=ConversationState.CONFIRMING_BOOKING,
            context={"pending_action": "book"}
        )

        return (
            "Please confirm: I will book an appointment on "
            f"{booking_context.get('date')} at {booking_context.get('time')} "
            f"with {booking_context.get('doctor_name') or booking_context.get('specialization')}. "
            "Reply with 'yes' to proceed or 'no' to cancel."
        )

    def _needs_doctor_data(self, intent: IntentType) -> bool:
        """Determine whether doctor data is required for an intent."""
        return intent in {
            IntentType.BOOK_APPOINTMENT,
            IntentType.GET_DOCTOR_INFO,
            IntentType.CHECK_AVAILABILITY
        }

    def _apply_rule_based_intent(
        self,
        message: str,
        intent_classification: IntentClassification
    ) -> IntentClassification:
        """Fallback intent detection using simple keyword rules."""
        text = message.strip().lower()

        rules = [
            (r"\b(book|schedule|appointment)\b", IntentType.BOOK_APPOINTMENT),
            (r"\b(reschedule|change|move)\b", IntentType.RESCHEDULE_APPOINTMENT),
            (r"\b(cancel|delete)\b", IntentType.CANCEL_APPOINTMENT),
            (r"\b(availability|available|slots)\b", IntentType.CHECK_AVAILABILITY),
            (r"\b(doctor|specialist|specialization|information)\b", IntentType.GET_DOCTOR_INFO),
            (r"\b(my appointments?|appointments list)\b", IntentType.GET_MY_APPOINTMENTS),
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
        """Fetch doctor data with simple in-memory caching."""
        now = time_module.time()
        if (
            now - self._doctor_cache["timestamp"] < self._doctor_cache_ttl_seconds
            and self._doctor_cache["data"]
        ):
            return self._doctor_cache["data"]

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

            if doctors:
                self._doctor_cache = {"timestamp": now, "data": doctors}
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
        return bool(re.search(r"\b(yes|y|yep|yeah|sure|confirm|ok|okay|please do)\b", normalized))

    def _is_negative(self, message: str) -> bool:
        """Check if a message is a negative response."""
        normalized = message.strip().lower()
        return bool(re.search(r"\b(no|n|cancel|stop|not now|don't|do not)\b", normalized))

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

    def _guess_specialization_from_text(
        self,
        message: str,
        doctor_data: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Infer specialization from free text with fuzzy matching."""
        if not message:
            return None

        text = message.lower()
        synonyms = self._specialization_synonyms()

        for key, value in synonyms.items():
            if key in text:
                return value

        known_specializations = {
            str(d.get("specialization")).lower()
            for d in doctor_data
            if isinstance(d, dict) and d.get("specialization")
        }

        for spec in known_specializations:
            if spec and spec in text:
                return self._normalize_specialization(spec)

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

    def _format_slots(self, slots: List[Dict[str, Any]]) -> str:
        """Format availability slots for display."""
        formatted = []
        for slot in slots[:5]:
            start = slot.get("start_time")
            end = slot.get("end_time")
            if start and end:
                formatted.append(f"{start}-{end}")
        return ", ".join(formatted) if formatted else "No slots available"

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

    def _parse_date(self, value: Optional[str]) -> Optional[date]:
        """Parse a date string into a date object."""
        if not value:
            return None
        try:
            return date_parser.parse(value, fuzzy=True).date()
        except Exception:
            return None

    def _parse_time(self, value: Optional[str]) -> Optional[dt_time]:
        """Parse a time string into a time object."""
        if not value:
            return None
        try:
            return date_parser.parse(value, fuzzy=True).time()
        except Exception:
            return None

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
                booking_payload = {
                    "doctor_email": doctor_email,
                    "patient_mobile_number": booking_context.get("patient_phone"),
                    "patient_name": booking_context.get("patient_name"),
                    "patient_email": booking_context.get("patient_email"),
                    "date": booking_date.isoformat(),
                    "start_time": booking_time.isoformat(),
                    "symptoms": booking_context.get("symptoms")
                }
                response = await calendar_client.book_appointment(booking_payload)

            self.conversation_manager.update_conversation(
                conversation_id=conversation_id,
                state=ConversationState.COMPLETED,
                context={"pending_action": None}
            )
            appointment_id = response.get("id") if isinstance(response, dict) else None
            return (
                f"Appointment booked successfully! "
                f"{'Appointment ID: ' + appointment_id if appointment_id else ''}"
            ).strip()
        except Exception as e:
            logger.error(f"Booking failed: {e}")
            return "I couldn't book the appointment due to an error. Please try again or choose another time."

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
                response = await calendar_client.reschedule_appointment(appointment_id, reschedule_payload)

            self.conversation_manager.update_conversation(
                conversation_id=conversation_id,
                state=ConversationState.COMPLETED,
                context={"pending_action": None}
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
                response = await calendar_client.cancel_appointment(appointment_id)

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