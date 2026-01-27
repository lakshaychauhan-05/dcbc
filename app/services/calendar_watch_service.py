"""
Calendar Watch Service - manages Google Calendar push notification channels.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid
import logging

from app.services.google_calendar_service import GoogleCalendarService
from app.models.calendar_watch import CalendarWatch
from app.config import settings

logger = logging.getLogger(__name__)


class CalendarWatchService:
    """Service for managing Google Calendar watch channels."""
    
    def __init__(self):
        self.calendar_service = GoogleCalendarService()
    
    def setup_watch_for_doctor(
        self,
        doctor_email: str,
        db: Session
    ) -> CalendarWatch:
        """
        Set up push notifications for a doctor's calendar.
        Creates a watch channel that receives notifications when calendar changes.

        Args:
            doctor_email: Doctor's Google Calendar email (unique identifier)
            db: Database session

        Returns:
            CalendarWatch object
        """
        try:
            service = self.calendar_service._get_service(doctor_email)
            
            # Generate unique channel ID
            channel_id = str(uuid.uuid4())
            
            # Webhook URL where Google will send notifications
            webhook_url = f"{settings.WEBHOOK_BASE_URL}/api/v1/webhooks/google-calendar"
            
            # Create watch request
            # Note: Google Calendar watches expire after max 7 days (604800000 ms)
            body = {
                'id': channel_id,
                'type': 'web_hook',
                'address': webhook_url,
                'token': settings.GOOGLE_CALENDAR_WEBHOOK_SECRET,
                'expiration': int((datetime.utcnow() + timedelta(days=7)).timestamp() * 1000)
            }
            
            # Execute watch request
            watch_response = service.events().watch(
                calendarId=doctor_email,
                body=body
            ).execute()
            
            # Store watch info in database
            calendar_watch = CalendarWatch(
                doctor_email=doctor_email,
                channel_id=channel_id,
                resource_id=watch_response['resourceId'],
                expiration=datetime.fromtimestamp(
                    int(watch_response['expiration']) / 1000
                ),
                is_active=True
            )
            
            db.add(calendar_watch)
            db.commit()
            db.refresh(calendar_watch)
            
            logger.info(
                f"Set up calendar watch for {doctor_email}: "
                f"channel_id={channel_id}, expires={calendar_watch.expiration}"
            )
            
            return calendar_watch
            
        except Exception as e:
            logger.error(f"Error setting up calendar watch: {str(e)}")
            raise
    
    def renew_watch(
        self,
        watch: CalendarWatch,
        db: Session
    ) -> CalendarWatch:
        """
        Renew expiring watch channel.
        
        Args:
            watch: Existing CalendarWatch to renew
            db: Database session
            
        Returns:
            New CalendarWatch object
        """
        try:
            # Stop old channel
            self.stop_watch(watch, db)
            
            # Create new watch
            new_watch = self.setup_watch_for_doctor(
                watch.doctor_email,
                db
            )
            
            logger.info(f"Renewed watch for {watch.doctor_email}")
            return new_watch
            
        except Exception as e:
            logger.error(f"Error renewing watch: {str(e)}")
            raise
    
    def stop_watch(
        self,
        watch: CalendarWatch,
        db: Session
    ):
        """
        Stop receiving notifications for a channel.
        
        Args:
            watch: CalendarWatch to stop
            db: Database session
        """
        try:
            service = self.calendar_service._get_service(watch.doctor_email)
            
            # Stop the channel
            service.channels().stop(
                body={
                    'id': watch.channel_id,
                    'resourceId': watch.resource_id
                }
            ).execute()
            
            # Mark as inactive in DB
            watch.is_active = False
            db.commit()
            
            logger.info(f"Stopped calendar watch: {watch.channel_id}")
            
        except Exception as e:
            logger.error(f"Error stopping watch: {str(e)}")
            # Continue anyway - mark as inactive
            watch.is_active = False
            db.commit()
    
    def renew_expiring_watches(self, db: Session):
        """
        Background job: Renew watches that are about to expire.
        Run this daily via cron or background worker.
        
        Args:
            db: Database session
        """
        # Find watches expiring in next 24 hours
        expiring_soon = db.query(CalendarWatch).filter(
            CalendarWatch.is_active == True,
            CalendarWatch.expiration < datetime.utcnow() + timedelta(days=1)
        ).all()
        
        logger.info(f"Found {len(expiring_soon)} watches expiring soon")
        
        for watch in expiring_soon:
            try:
                self.renew_watch(watch, db)
                logger.info(f"✓ Renewed watch for {watch.doctor_email}")
            except Exception as e:
                logger.error(f"✗ Failed to renew watch for {watch.doctor_email}: {e}")
    
    def get_channel_info(self, channel_id: str, db: Session) -> dict:
        """
        Retrieve channel info from database.

        Args:
            channel_id: Google Calendar channel ID
            db: Database session

        Returns:
            Dictionary with doctor_email, or None if not found
        """
        watch = db.query(CalendarWatch).filter(
            CalendarWatch.channel_id == channel_id,
            CalendarWatch.is_active == True
        ).first()
        
        if watch:
            return {
                'doctor_email': watch.doctor_email
            }
        return None
