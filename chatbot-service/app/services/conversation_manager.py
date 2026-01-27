"""
Conversation Manager for handling chat state and context.
"""
import uuid
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

from app.core.config import settings
from app.models.chat import (
    Conversation,
    ConversationState,
    ChatMessage,
    MessageRole,
    BookingDetails
)

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation state and context."""

    def __init__(self):
        # In-memory storage for conversations (use Redis in production)
        self._conversations: Dict[str, Conversation] = {}
        self._user_conversations: Dict[str, List[str]] = defaultdict(list)

    def create_conversation(self, user_id: Optional[str] = None) -> Conversation:
        """Create a new conversation."""
        conversation_id = str(uuid.uuid4())

        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            state=ConversationState.INITIAL,
            context={},
            expires_at=datetime.utcnow() + timedelta(minutes=settings.CONVERSATION_TIMEOUT_MINUTES)
        )

        self._conversations[conversation_id] = conversation

        if user_id:
            self._user_conversations[user_id].append(conversation_id)
            # Keep only recent conversations per user
            if len(self._user_conversations[user_id]) > 10:
                old_conversation_id = self._user_conversations[user_id].pop(0)
                self._conversations.pop(old_conversation_id, None)

        logger.info(f"Created conversation {conversation_id} for user {user_id}")
        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        conversation = self._conversations.get(conversation_id)

        if conversation and conversation.expires_at:
            if datetime.utcnow() > conversation.expires_at:
                # Conversation expired
                self._conversations.pop(conversation_id, None)
                return None

        return conversation

    def update_conversation(
        self,
        conversation_id: str,
        state: Optional[ConversationState] = None,
        context: Optional[Dict[str, Any]] = None,
        add_message: Optional[ChatMessage] = None
    ) -> Optional[Conversation]:
        """Update a conversation."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        if state is not None:
            conversation.state = state

        if context is not None:
            conversation.context.update(context)

        if add_message is not None:
            conversation.messages.append(add_message)
            # Keep only recent messages
            max_messages = self._max_history_messages()
            if len(conversation.messages) > max_messages:
                conversation.messages = conversation.messages[-max_messages:]

        conversation.updated_at = datetime.utcnow()

        # Extend expiration
        conversation.expires_at = datetime.utcnow() + timedelta(minutes=settings.CONVERSATION_TIMEOUT_MINUTES)

        return conversation

    def _max_history_messages(self) -> int:
        """Compute max messages to keep based on turn settings."""
        turns = getattr(settings, "MAX_CONVERSATION_TURNS", None)
        if isinstance(turns, int) and turns > 0:
            return turns * 2
        return settings.MAX_CONVERSATION_HISTORY

    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ChatMessage]:
        """Add a message to a conversation."""
        message = ChatMessage(
            role=role,
            content=content,
            metadata=metadata
        )

        conversation = self.update_conversation(
            conversation_id=conversation_id,
            add_message=message
        )

        return message if conversation else None

    def get_conversation_history(self, conversation_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        """Get conversation history."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []

        max_messages = limit or self._max_history_messages()
        return conversation.messages[-max_messages:]

    def get_booking_context(self, conversation_id: str) -> Optional[BookingDetails]:
        """Extract booking details from conversation context."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        context = conversation.context
        return BookingDetails(
            appointment_id=context.get("appointment_id"),
            doctor_email=context.get("doctor_email"),
            date=context.get("date"),
            time=context.get("time"),
            patient_name=context.get("patient_name"),
            patient_phone=context.get("patient_phone"),
            patient_email=context.get("patient_email"),
            symptoms=context.get("symptoms"),
            appointment_type=context.get("appointment_type"),
            reschedule_date=context.get("reschedule_date"),
            reschedule_time=context.get("reschedule_time")
        )

    def update_booking_context(self, conversation_id: str, booking_details: Dict[str, Any]) -> bool:
        """Update booking context in conversation."""
        return self.update_conversation(
            conversation_id=conversation_id,
            context=booking_details
        ) is not None

    def clear_conversation_context(self, conversation_id: str) -> bool:
        """Clear conversation context."""
        return self.update_conversation(
            conversation_id=conversation_id,
            context={},
            state=ConversationState.INITIAL
        ) is not None

    def get_user_conversations(self, user_id: str) -> List[Conversation]:
        """Get all active conversations for a user."""
        conversation_ids = self._user_conversations.get(user_id, [])
        conversations = []

        for conv_id in conversation_ids:
            conversation = self.get_conversation(conv_id)
            if conversation:
                conversations.append(conversation)

        return conversations

    def cleanup_expired_conversations(self) -> int:
        """Clean up expired conversations. Returns number of cleaned conversations."""
        now = datetime.utcnow()
        expired_ids = []

        for conv_id, conversation in self._conversations.items():
            if conversation.expires_at and now > conversation.expires_at:
                expired_ids.append(conv_id)

        for conv_id in expired_ids:
            conversation = self._conversations.pop(conv_id, None)
            if conversation and conversation.user_id:
                self._user_conversations[conversation.user_id] = [
                    cid for cid in self._user_conversations[conversation.user_id]
                    if cid != conv_id
                ]

        logger.info(f"Cleaned up {len(expired_ids)} expired conversations")
        return len(expired_ids)