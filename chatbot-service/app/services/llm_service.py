"""
LLM Service for intent classification and entity extraction using LangChain.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from app.core.config import settings
from app.models.chat import (
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
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            api_key=settings.OPENAI_API_KEY
        )

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

    def _create_intent_prompt(self) -> ChatPromptTemplate:
        """Create prompt template for intent classification."""
        template = """You are an AI assistant for a medical appointment booking system. Your task is to analyze user messages and classify their intent.

Available intents:
- book_appointment: User wants to schedule a new appointment
- reschedule_appointment: User wants to change an existing appointment
- cancel_appointment: User wants to cancel an existing appointment
- get_doctor_info: User wants information about doctors or their specialties
- check_availability: User wants to check available appointment slots
- get_my_appointments: User wants to see their existing appointments
- general_info: General questions about the clinic, services, etc.
- unknown: Unable to determine intent

Guidelines:
- Be precise in your classification
- Look for keywords and context clues
- Consider the conversation flow
- If uncertain, prefer more specific intents over general ones

Conversation history (most recent last):
{history}

User message: {message}

Return only a JSON object with the following structure:
{{
    "intent": "intent_type",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""

        return ChatPromptTemplate.from_template(template)

    def _create_entity_prompt(self) -> ChatPromptTemplate:
        """Create prompt template for entity extraction."""
        template = """Extract relevant entities from the user's message for appointment booking.

Available entity types:
- date: Dates (e.g., "tomorrow", "next Monday", "2024-01-15")
- time: Times (e.g., "2 PM", "14:00", "morning")
- doctor_name: Doctor names (e.g., "Dr. Smith", "Dr. Sarah Johnson")
- specialization: Medical specialties (e.g., "cardiology", "dermatology")
- patient_name: Patient names (if mentioned)
- phone_number: Phone numbers
- email: Email addresses
- symptoms: Medical symptoms or conditions

Conversation history (most recent last):
{history}

Guidelines:
- Use history to resolve pronouns like "him/her/that doctor" into a doctor_name when possible.

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

        return ChatPromptTemplate.from_template(template)

    def _create_response_prompt(self) -> ChatPromptTemplate:
        """Create prompt template for generating responses."""
        template = """You are a helpful medical appointment booking assistant. Use the provided context to respond naturally and helpfully.

Context:
- Intent: {intent}
- Entities: {entities}
- Conversation history: {history}
- Doctor information: {doctor_info}

Guidelines for responses:
- Be friendly and professional
- Ask clarifying questions when information is missing
- Confirm details before booking
- Provide clear next steps
- Use simple language

User message: {message}

Generate a helpful response:"""

        return ChatPromptTemplate.from_template(template)

    async def classify_intent(self, message: str, context: Optional[List[ChatMessage]] = None) -> IntentClassification:
        """Classify the intent of a user message."""
        try:
            # Prepare conversation history
            history_text = self._format_history(context)

            # Call LLM for intent classification
            chain = self.intent_prompt | self.llm
            response = await chain.ainvoke({
                "message": message,
                "history": history_text
            })

            # Parse response
            response_text = response.content.strip()

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
            chain = self.entity_prompt | self.llm
            response = await chain.ainvoke({
                "message": message,
                "history": self._format_history(context)
            })

            response_text = response.content.strip()

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

            # Generate response
            chain = self.response_prompt | self.llm
            response = await chain.ainvoke({
                "message": message,
                "intent": intent.intent.value,
                "entities": entities_text,
                "history": history_text,
                "doctor_info": doctor_text
            })

            return response.content.strip()

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm sorry, I encountered an error. Could you please try again?"

    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return bool(settings.OPENAI_API_KEY)