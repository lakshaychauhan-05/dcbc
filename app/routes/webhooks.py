"""
Webhook handlers for external service integrations.
"""
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.database import get_db
from app.services.calendar_sync_service import CalendarSyncService
from app.services.calendar_watch_service import CalendarWatchService
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()
calendar_sync_service = CalendarSyncService()
calendar_watch_service = CalendarWatchService()


@router.post("/google-calendar")
async def handle_google_calendar_notification(
    request: Request,
    x_goog_channel_id: Optional[str] = Header(None),
    x_goog_channel_token: Optional[str] = Header(None),
    x_goog_resource_id: Optional[str] = Header(None),
    x_goog_resource_state: Optional[str] = Header(None),
    x_goog_resource_uri: Optional[str] = Header(None),
    x_goog_message_number: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Receives push notifications from Google Calendar.
    Triggered when doctor updates their calendar.
    
    Resource States:
    - sync: Initial notification when watch is established
    - exists: Periodic confirmation that channel is valid
    - not_exists: Channel expired or was cancelled
    - (no state header): Actual calendar change event
    
    This endpoint enables real-time synchronization from Google Calendar to Database.
    """
    logger.info(
        f"Received Google Calendar notification: "
        f"channel_id={x_goog_channel_id}, "
        f"state={x_goog_resource_state}, "
        f"resource={x_goog_resource_id}, "
        f"msg_num={x_goog_message_number}"
    )
    
    # 1. Verify webhook authenticity
    if not verify_google_webhook(x_goog_channel_token):
        logger.warning(f"Invalid webhook token: {x_goog_channel_token}")
        raise HTTPException(status_code=401, detail="Invalid webhook token")
    
    # 2. Handle different resource states
    if x_goog_resource_state == "sync":
        # Initial sync notification when watch is established
        logger.info("Initial sync notification received")
        return {"status": "sync_acknowledged"}
    
    elif x_goog_resource_state == "exists":
        # Periodic check that channel still exists
        logger.info("Channel existence check")
        return {"status": "exists_acknowledged"}
    
    elif x_goog_resource_state == "not_exists":
        # Channel expired or was cancelled
        logger.warning(f"Channel no longer exists: {x_goog_channel_id}")
        # TODO: Implement automatic renewal
        return {"status": "channel_expired"}
    
    # 3. Process actual calendar changes
    try:
        # Get doctor email from channel_id (stored in DB)
        channel_info = calendar_watch_service.get_channel_info(x_goog_channel_id, db)
        
        if not channel_info:
            logger.error(f"Unknown channel ID: {x_goog_channel_id}")
            raise HTTPException(status_code=404, detail="Channel not found")
        
        doctor_email = channel_info['doctor_email']
        
        # 4. Sync calendar changes to database
        result = await calendar_sync_service.sync_calendar_to_db(
            doctor_email=doctor_email,
            db=db
        )
        
        logger.info(f"Calendar sync completed for {doctor_email}: {result}")
        return {
            "status": "synced",
            "doctor_email": doctor_email,
            "stats": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing calendar notification: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process notification: {str(e)}"
        )


def verify_google_webhook(channel_token: Optional[str]) -> bool:
    """
    Verify that webhook is from Google.
    Compares the token sent by Google with our stored secret.
    
    Args:
        channel_token: Token from X-Goog-Channel-Token header
        
    Returns:
        True if token is valid, False otherwise
    """
    if not channel_token:
        return False
    
    # Compare with stored token
    return channel_token == settings.GOOGLE_CALENDAR_WEBHOOK_SECRET


@router.get("/google-calendar/test")
async def test_webhook():
    """
    Test endpoint to verify webhook is accessible.
    Public endpoint (no auth required) for testing.
    """
    return {
        "status": "ok",
        "message": "Webhook endpoint is accessible",
        "webhook_url": f"http://localhost:8005/api/v1/webhooks/google-calendar"
    }
