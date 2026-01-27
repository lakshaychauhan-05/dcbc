"""
Pydantic models for chat functionality.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Role of a chat message."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """A single chat message."""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class ConversationState(str, Enum):
    """State of a conversation."""
    INITIAL = "initial"
    GATHERING_INFO = "gathering_info"
    CONFIRMING_BOOKING = "confirming_booking"
    BOOKING_APPOINTMENT = "booking_appointment"
    COMPLETED = "completed"
    ERROR = "error"


class IntentType(str, Enum):
    """Types of user intents."""
    BOOK_APPOINTMENT = "book_appointment"
    RESCHEDULE_APPOINTMENT = "reschedule_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    GET_DOCTOR_INFO = "get_doctor_info"
    CHECK_AVAILABILITY = "check_availability"
    GET_MY_APPOINTMENTS = "get_my_appointments"
    GENERAL_INFO = "general_info"
    UNKNOWN = "unknown"


class EntityType(str, Enum):
    """Types of entities that can be extracted."""
    DATE = "date"
    TIME = "time"
    DOCTOR_NAME = "doctor_name"
    SPECIALIZATION = "specialization"
    PATIENT_NAME = "patient_name"
    PHONE_NUMBER = "phone_number"
    EMAIL = "email"
    SYMPTOMS = "symptoms"


class ExtractedEntity(BaseModel):
    """An entity extracted from user message."""
    type: EntityType
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None


class IntentClassification(BaseModel):
    """Result of intent classification."""
    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    entities: List[ExtractedEntity] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """Request to send a message to the chatbot."""
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Response from the chatbot."""
    conversation_id: str
    message: str
    intent: Optional[IntentClassification] = None
    suggested_actions: Optional[List[str]] = []
    requires_confirmation: bool = False
    booking_details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    """A conversation session."""
    id: str
    user_id: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list)
    state: ConversationState = ConversationState.INITIAL
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class BookingDetails(BaseModel):
    """Details for appointment booking."""
    appointment_id: Optional[str] = None
    doctor_email: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_email: Optional[str] = None
    symptoms: Optional[str] = None
    appointment_type: Optional[str] = None
    reschedule_date: Optional[str] = None
    reschedule_time: Optional[str] = None


class DoctorInfo(BaseModel):
    """Doctor information for chatbot context."""
    email: str
    name: str
    specialization: str
    experience_years: int
    languages: List[str]
    consultation_type: str
    working_days: List[str]
    working_hours: Dict[str, str]
    slot_duration_minutes: int
    rating: Optional[float] = None
    patient_reviews: Optional[int] = None
    expertise_areas: Optional[List[str]] = None