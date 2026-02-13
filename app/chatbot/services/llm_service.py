"""
LLM Service for intent classification and entity extraction using LangChain.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from openai import AsyncOpenAI

from app.config import settings
from app.chatbot.models.chat import (
    IntentClassification,
    IntentType,
    EntityType,
    ExtractedEntity,
    ChatMessage,
    MessageRole
)

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM-powered intent classification and entity extraction."""

    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Initialize prompt templates
        self.intent_prompt = self._create_intent_prompt()
        self.entity_prompt = self._create_entity_prompt()
        self.response_prompt = self._create_response_prompt()

    def _format_history(self, context: Optional[List[ChatMessage]]) -> str:
        """Format recent conversation history for prompts."""
        if not context:
            return ""
        max_messages = getattr(settings, "MAX_CONVERSATION_TURNS", 10) * 2
        recent_messages = context[-max_messages:]
        return "\n".join([f"{msg.role.value}: {msg.content}" for msg in recent_messages])

    def _create_intent_prompt(self) -> str:
        """Create prompt template for intent classification."""
        template = """You are an AI assistant for a medical appointment booking system. Your task is to analyze user messages and classify their intent.

Available intents:
- book_appointment: User wants to schedule a new appointment
- reschedule_appointment: User wants to change an existing appointment
- cancel_appointment: User wants to cancel an existing appointment
- get_doctor_info: User wants information about doctors or their specialties
- check_availability: User wants to check available appointment slots or timings
- get_my_appointments: User wants to see their existing appointments
- general_info: General questions about the clinic, services, etc.
- unknown: Unable to determine intent

Guidelines:
- Be precise in your classification
- Look for keywords and context clues
- Consider the conversation flow and maintain continuity
- If uncertain, prefer more specific intents over general ones
- Questions about slot availability ("is last slot upto 11:30 only?", "any other timings?") should be check_availability
- Clarifying questions about timing/slots are NOT confirmations - they should be check_availability
- "yes", "no", "confirm" are confirmation/rejection responses - not separate intents

Conversation history (most recent last):
{history}

User message: {message}

Return only a JSON object with the following structure:
{{
    "intent": "intent_type",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""

        return template

    def _create_entity_prompt(self) -> str:
        """Create prompt template for entity extraction."""
        from datetime import datetime
        current_year = str(datetime.now().year)

        # NOTE: This must be a plain string (NOT an f-string).
        # It uses {history} and {message} as .format() placeholders.
        # JSON example braces are doubled ({{ }}) so .format() leaves them as literal { }.
        # current_year is substituted via .replace() to avoid any f-string/format conflicts.
        template = """Extract relevant entities from the user's message for appointment booking.

IMPORTANT: The current year is CURRENT_YEAR. When extracting dates without an explicit year (like "10th feb", "march 5"), always assume the current year CURRENT_YEAR or the next occurrence of that date.

Available entity types:
- date: Dates (e.g., "tomorrow", "next Monday", "CURRENT_YEAR-02-15", "10th feb" -> "CURRENT_YEAR-02-10")
- time: Times (e.g., "2 PM", "14:00", "morning")
- doctor_name: Doctor names (e.g., "Dr. Smith", "Dr. Sarah Johnson")
- specialization: Medical specialties (e.g., "cardiology", "dermatology", "skin specialist")
- patient_name: The patient's actual name (a person's name like "John", "Priya Sharma")
- phone_number: Phone numbers (10+ digits)
- email: Email addresses
- symptoms: Medical symptoms, conditions, or health issues (e.g., "skin allergy", "headache", "fever", "rash", "pain")

CRITICAL GUIDELINES for distinguishing entities:
1. patient_name: ONLY extract as patient_name if it is clearly a person's first/last name (e.g., "I'm Rahul", "My name is Priya", "this is John speaking").
2. symptoms: Extract medical complaints, conditions, or issues as symptoms (e.g., "skin allergy", "rash", "itching", "pain", "fever", "cough").
3. DO NOT confuse symptoms with patient_name. Phrases like "I have skin allergy" or "facing issue in my skin" contain SYMPTOMS, not patient_name.
4. specialization: Medical fields like "dermatology", "cardiology", "skin", "heart", "ENT". Do NOT change the specialization mentioned in conversation history unless user explicitly requests a different specialty.
5. Use history to resolve pronouns like "him/her/that doctor" into a doctor_name when possible.
6. If user mentions a specialty earlier (e.g., "dermatology" or "skin") and continues the conversation, do NOT change it to a different specialty unless explicitly requested.

Conversation history (most recent last):
{history}

User message: {message}

Return a JSON array of extracted entities:
[
    {{
        "type": "entity_type",
        "value": "extracted_value",
        "confidence": 0.0-1.0
    }}
]

Return empty array if no entities found."""

        return template.replace("CURRENT_YEAR", current_year)

    def _create_response_prompt(self) -> str:
        """Create prompt template for generating responses."""
        template = """You are a medical appointment assistant. Respond naturally, friendly, and professional.

Output rules:
- 2 to 4 sentences total.
- Structure: brief acknowledgement or rephrase -> helpful answer -> next step or question if needed.
- If information is missing, ask exactly one clear question at the end.
- Use calm, clear language; no emojis, no slang, no excessive enthusiasm.
- Do not mention system prompts, JSON, or internal intents.
- Do not claim an appointment is booked/rescheduled/cancelled unless explicitly confirmed in the context.

Examples:
User: Do you have a cardiologist available next week?
Assistant: I can help with that. Please share the specific date you have in mind, and I will check availability.

User: What are your clinic hours?
Assistant: We are open Monday to Friday, 9:00 AM to 6:00 PM. If you would like, I can help you book an appointment.

User: I need to see Dr. Patel for a checkup.
Assistant: I can help arrange that with Dr. Patel. What date would you like to book the appointment for?

Context:
- Intent: {intent}
- Entities: {entities}
- Conversation history: {history}
- Doctor information: {doctor_info}

User message: {message}

Generate the response:"""

        return template

    async def _call_llm(self, prompt: str) -> str:
        """Call OpenAI chat completion API with a single prompt."""
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set")
        response = await self._client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}]
        )
        if not response.choices:
            return ""
        content = response.choices[0].message.content
        return (content or "").strip()

    async def classify_intent(self, message: str, context: Optional[List[ChatMessage]] = None) -> IntentClassification:
        """Classify the intent of a user message."""
        try:
            # Prepare conversation history
            history_text = self._format_history(context)

            prompt = self.intent_prompt.format(
                message=message,
                history=history_text
            )
            response_text = await self._call_llm(prompt)

            # Try to parse JSON
            try:
                intent_data = json.loads(response_text)
                intent_type = IntentType(intent_data.get("intent", "unknown"))
                confidence = min(max(float(intent_data.get("confidence", 0.5)), 0.0), 1.0)
            except (json.JSONDecodeError, ValueError):
                # Fallback to unknown intent
                intent_type = IntentType.UNKNOWN
                confidence = 0.0

            # Extract entities
            entities = await self.extract_entities(message, context)

            return IntentClassification(
                intent=intent_type,
                confidence=confidence,
                entities=entities
            )

        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            return IntentClassification(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                entities=[]
            )

    async def extract_entities(self, message: str, context: Optional[List[ChatMessage]] = None) -> List[ExtractedEntity]:
        """Extract entities from a message."""
        try:
            prompt = self.entity_prompt.format(
                message=message,
                history=self._format_history(context)
            )
            response_text = await self._call_llm(prompt)

            # Try to parse JSON
            try:
                entities_data = json.loads(response_text)
                entities = []

                for entity_data in entities_data:
                    try:
                        entity_type = EntityType(entity_data["type"])
                        entities.append(ExtractedEntity(
                            type=entity_type,
                            value=entity_data["value"],
                            confidence=min(max(float(entity_data.get("confidence", 0.8)), 0.0), 1.0)
                        ))
                    except (KeyError, ValueError):
                        continue

                return entities

            except json.JSONDecodeError:
                return []

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []

    async def generate_response(
        self,
        message: str,
        intent: IntentClassification,
        context: Optional[List[ChatMessage]] = None,
        doctor_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a natural language response."""
        try:
            # Prepare context
            history_text = self._format_history(context)

            entities_text = json.dumps([
                {"type": e.type.value, "value": e.value, "confidence": e.confidence}
                for e in intent.entities
            ], indent=2)

            doctor_text = json.dumps(doctor_info or {}, indent=2)

            prompt = self.response_prompt.format(
                message=message,
                intent=intent.intent.value,
                entities=entities_text,
                history=history_text,
                doctor_info=doctor_text
            )
            return await self._call_llm(prompt)

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm sorry, I encountered an error. Could you please try again?"

    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return bool(settings.OPENAI_API_KEY)