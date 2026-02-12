"""
Conversation Manager for handling chat state and context.
"""
import uuid
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone

import redis

from app.config import settings
from app.chatbot.models.chat import (
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
        self._redis = None
        self._memory_store: Dict[str, Conversation] = {}
        self._user_conversations: Dict[str, List[str]] = {}

        if settings.REDIS_URL:
            try:
                self._redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
                self._redis.ping()
            except Exception as e:
                logger.warning(f"Redis unavailable, using in-memory store: {e}")
                self._redis = None

        self._max_history_terms = 20
        self._max_user_conversations = 20

    def _conversation_key(self, conversation_id: str) -> str:
        return f"conversation:{conversation_id}"

    def _user_conversations_key(self, user_id: str) -> str:
        return f"user_conversations:{user_id}"

    def _ttl_seconds(self) -> int:
        return int(settings.CONVERSATION_TIMEOUT_MINUTES * 60)

    def _serialize_conversation(self, conversation: Conversation) -> str:
        def serialize_message(msg: ChatMessage) -> Dict[str, Any]:
            return {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata
            }

        payload = {
            "id": conversation.id,
            "user_id": conversation.user_id,
            "messages": [serialize_message(m) for m in conversation.messages],
            "state": conversation.state.value,
            "context": conversation.context,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "expires_at": conversation.expires_at.isoformat() if conversation.expires_at else None
        }
        return json.dumps(payload)

    def _deserialize_conversation(self, data: str) -> Conversation:
        payload = json.loads(data)

        def parse_dt(value: Optional[str]) -> Optional[datetime]:
            if not value:
                return None
            return datetime.fromisoformat(value)

        messages = []
        for msg in payload.get("messages", []):
            try:
                messages.append(ChatMessage(
                    role=MessageRole(msg.get("role")),
                    content=msg.get("content"),
                    timestamp=parse_dt(msg.get("timestamp")) or datetime.now(timezone.utc),
                    metadata=msg.get("metadata")
                ))
            except Exception:
                continue

        return Conversation(
            id=payload.get("id"),
            user_id=payload.get("user_id"),
            messages=messages,
            state=ConversationState(payload.get("state", ConversationState.INITIAL.value)),
            context=payload.get("context") or {},
            created_at=parse_dt(payload.get("created_at")) or datetime.now(timezone.utc),
            updated_at=parse_dt(payload.get("updated_at")) or datetime.now(timezone.utc),
            expires_at=parse_dt(payload.get("expires_at"))
        )

    def create_conversation(self, user_id: Optional[str] = None) -> Conversation:
        """Create a new conversation."""
        conversation_id = str(uuid.uuid4())

        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            state=ConversationState.INITIAL,
            context={},
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.CONVERSATION_TIMEOUT_MINUTES)
        )

        if self._redis:
            self._redis.setex(
                self._conversation_key(conversation_id),
                self._ttl_seconds(),
                self._serialize_conversation(conversation)
            )
            if user_id:
                key = self._user_conversations_key(user_id)
                self._redis.rpush(key, conversation_id)
                self._redis.ltrim(key, -self._max_user_conversations, -1)
                self._redis.expire(key, self._ttl_seconds())
        else:
            self._memory_store[conversation_id] = conversation
            if user_id:
                existing = self._user_conversations.get(user_id, [])
                existing.append(conversation_id)
                self._user_conversations[user_id] = existing[-self._max_user_conversations:]

        logger.info(f"Created conversation {conversation_id} for user {user_id}")
        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        conversation = None
        if self._redis:
            data = self._redis.get(self._conversation_key(conversation_id))
            if data:
                conversation = self._deserialize_conversation(data)
        else:
            conversation = self._memory_store.get(conversation_id)

        if conversation and conversation.expires_at:
            if datetime.now(timezone.utc) > conversation.expires_at:
                # Conversation expired
                if self._redis:
                    self._redis.delete(self._conversation_key(conversation_id))
                else:
                    self._memory_store.pop(conversation_id, None)
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

        conversation.updated_at = datetime.now(timezone.utc)

        # Extend expiration
        conversation.expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.CONVERSATION_TIMEOUT_MINUTES)

        if self._redis:
            self._redis.setex(
                self._conversation_key(conversation_id),
                self._ttl_seconds(),
                self._serialize_conversation(conversation)
            )
        else:
            self._memory_store[conversation_id] = conversation
        return conversation

    def _max_history_messages(self) -> int:
        """Compute max messages to keep based on turn settings."""
        turns = getattr(settings, "MAX_CONVERSATION_TURNS", None)
        if isinstance(turns, int) and turns > 0:
            return min(turns * 2, self._max_history_terms)
        return min(settings.MAX_CONVERSATION_HISTORY, self._max_history_terms)

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
        if self._redis:
            key = self._user_conversations_key(user_id)
            conversation_ids = self._redis.lrange(key, 0, -1) or []
        else:
            conversation_ids = self._user_conversations.get(user_id, [])
        conversations = []

        for conv_id in conversation_ids:
            conversation = self.get_conversation(conv_id)
            if conversation:
                conversations.append(conversation)

        return conversations

    def cleanup_expired_conversations(self) -> int:
        """Clean up expired conversations. Returns number of cleaned conversations."""
        if self._redis:
            # Redis handles expiration automatically
            return 0
        removed = 0
        now = datetime.now(timezone.utc)
        for conv_id, conversation in list(self._memory_store.items()):
            if conversation.expires_at and now > conversation.expires_at:
                self._memory_store.pop(conv_id, None)
                removed += 1
        return removed