"""
Chat API routes for the Chatbot Service.
"""
from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import logging

from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.conversation_manager import ConversationManager

router = APIRouter()
chat_service = ChatService()
conversation_manager = ConversationManager()
logger = logging.getLogger(__name__)

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


@router.post("/", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """
    Send a message to the chatbot and get a response.

    This endpoint processes user messages, classifies intent,
    manages conversation state, and generates appropriate responses.
    """
    try:
        response = await chat_service.process_message(request)
        return response

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(e)}"
        )


@router.get("/conversation/{conversation_id}")
async def get_conversation_history(conversation_id: str, limit: int = 50):
    """Get conversation history for a specific conversation."""
    try:
        messages = conversation_manager.get_conversation_history(conversation_id, limit)

        # Convert to dict format
        message_dicts = []
        for msg in messages:
            message_dicts.append({
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata
            })

        return {
            "conversation_id": conversation_id,
            "messages": message_dicts,
            "count": len(message_dicts)
        }

    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation history: {str(e)}"
        )


@router.delete("/conversation/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear conversation context and reset state."""
    try:
        success = conversation_manager.clear_conversation_context(conversation_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )

        return {"message": "Conversation cleared successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear conversation: {str(e)}"
        )


@router.post("/conversation/{conversation_id}/confirm")
async def confirm_action(conversation_id: str, action_data: Dict = None):
    """
    Confirm and execute a pending action (like booking an appointment).
    """
    try:
        response_text = await chat_service._execute_pending_action(conversation_id)
        return {
            "conversation_id": conversation_id,
            "status": "confirmed",
            "message": response_text
        }

    except Exception as e:
        logger.error(f"Error confirming action: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm action: {str(e)}"
        )


@router.websocket("/ws/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    """
    WebSocket endpoint for real-time chat.

    Allows for real-time bidirectional communication with the chatbot.
    """
    await websocket.accept()
    active_connections[conversation_id] = websocket

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # Create chat request
            chat_request = ChatRequest(
                message=message_data.get("message", ""),
                conversation_id=conversation_id,
                user_id=message_data.get("user_id"),
                metadata=message_data.get("metadata", {})
            )

            # Process message
            response = await chat_service.process_message(chat_request)

            # Send response back
            await websocket.send_json(response.dict())

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for conversation {conversation_id}")
    except Exception as e:
        logger.error(f"WebSocket error for conversation {conversation_id}: {e}")
        try:
            await websocket.send_json({
                "error": "An error occurred processing your message",
                "conversation_id": conversation_id
            })
        except:
            pass  # Connection might be closed
    finally:
        active_connections.pop(conversation_id, None)


@router.get("/active-connections")
async def get_active_connections():
    """Get count of active WebSocket connections (for monitoring)."""
    return {
        "active_connections": len(active_connections),
        "connections": list(active_connections.keys())
    }