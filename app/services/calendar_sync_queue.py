"""
Calendar Sync Queue - persistent worker for Google Calendar sync jobs.
"""
import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import inspect

from app.config import settings
from app.database import SessionLocal
from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient
from app.models.calendar_sync_job import CalendarSyncJob
from app.services.google_calendar_service import GoogleCalendarService

logger = logging.getLogger(__name__)


class CalendarSyncQueue:
    """Background queue for retrying calendar sync."""

    def __init__(
        self,
        max_retries: int = settings.CALENDAR_SYNC_MAX_RETRIES,
        retry_base_seconds: int = settings.CALENDAR_SYNC_RETRY_BASE_SECONDS,
        poll_interval_seconds: int = settings.CALENDAR_SYNC_POLL_INTERVAL_SECONDS
    ):
        self._worker: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._max_retries = max_retries
        self._retry_base = retry_base_seconds
        self._poll_interval = poll_interval_seconds
        self._calendar_service = GoogleCalendarService()

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        if not self._calendar_sync_table_available():
            logger.warning(
                "Calendar sync queue not started: calendar_sync_jobs table missing. "
                "Run migrations to create it."
            )
            return
        self._stop_event.clear()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()
        logger.info("Calendar sync queue started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._worker:
            self._worker.join(timeout=5)

    def is_running(self) -> bool:
        return bool(self._worker and self._worker.is_alive())

    def enqueue_create(self, appointment_id: str) -> None:
        self._enqueue(appointment_id, "CREATE")

    def enqueue_update(self, appointment_id: str) -> None:
        self._enqueue(appointment_id, "UPDATE")

    def enqueue_delete(self, appointment_id: str) -> None:
        self._enqueue(appointment_id, "DELETE")

    def _enqueue(self, appointment_id: str, action: str) -> None:
        if not appointment_id:
            return
        db = SessionLocal()
        try:
            job = (
                db.query(CalendarSyncJob)
                .filter(
                    CalendarSyncJob.appointment_id == UUID(appointment_id),
                    CalendarSyncJob.action == action,
                    CalendarSyncJob.status.in_(["PENDING", "IN_PROGRESS"])
                )
                .first()
            )
            if job:
                return
            new_job = CalendarSyncJob(
                appointment_id=UUID(appointment_id),
                action=action,
                status="PENDING"
            )
            db.add(new_job)

            appointment = db.query(Appointment).filter(Appointment.id == UUID(appointment_id)).first()
            if appointment:
                appointment.calendar_sync_status = "PENDING"

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to enqueue calendar sync job: {e}")
        finally:
            db.close()

    def trigger_immediate_sync(self, appointment_id: str, action: str = "CREATE") -> None:
        """
        Process the sync job for this appointment once, in the current thread.
        Intended to be called from a background thread right after enqueue_create
        so the calendar event is created within ~1-2 seconds without blocking the request.
        Claims the job (IN_PROGRESS, attempts += 1) so the poll worker does not double-process.
        """
        if not appointment_id:
            return
        db = SessionLocal()
        job_id = None
        try:
            job = (
                db.query(CalendarSyncJob)
                .filter(
                    CalendarSyncJob.appointment_id == UUID(appointment_id),
                    CalendarSyncJob.action == action,
                    CalendarSyncJob.status == "PENDING",
                )
                .with_for_update(skip_locked=True)
                .first()
            )
            if job:
                job.status = "IN_PROGRESS"
                job.attempts += 1
                db.add(job)
                db.commit()
                job_id = job.id
        except Exception as e:
            db.rollback()
            logger.warning(f"Trigger immediate sync: could not find job for {appointment_id}: {e}")
        finally:
            db.close()
        if job_id:
            self._process_job(job_id)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._process_batch()
            except Exception as e:
                logger.error(f"Calendar sync worker error: {e}")
            time.sleep(self._poll_interval)

    def _process_batch(self) -> None:
        db = SessionLocal()
        now = datetime.now(timezone.utc)
        jobs = []
        try:
            jobs = (
                db.query(CalendarSyncJob)
                .filter(
                    CalendarSyncJob.status == "PENDING",
                    CalendarSyncJob.next_attempt_at <= now
                )
                .with_for_update(skip_locked=True)
                .limit(10)
                .all()
            )
            for job in jobs:
                job.status = "IN_PROGRESS"
                job.attempts += 1
                db.add(job)
            db.commit()
        finally:
            db.close()

        for job in jobs:
            self._process_job(job.id)

    def _calendar_sync_table_available(self) -> bool:
        db = SessionLocal()
        try:
            inspector = inspect(db.get_bind())
            return inspector.has_table("calendar_sync_jobs")
        except Exception as e:
            logger.warning(f"Calendar sync table check failed: {e}")
            return False
        finally:
            db.close()

    def _process_job(self, job_id) -> None:
        db = SessionLocal()
        try:
            job = db.query(CalendarSyncJob).filter(CalendarSyncJob.id == job_id).first()
            if not job:
                return
            appointment = db.query(Appointment).filter(Appointment.id == job.appointment_id).first()
            if not appointment:
                job.status = "FAILED"
                job.last_error = "Appointment not found"
                db.commit()
                return

            if job.action in {"CREATE", "UPDATE"}:
                if appointment.status == AppointmentStatus.CANCELLED:
                    job.status = "COMPLETED"
                    appointment.calendar_sync_status = "SYNCED"
                    appointment.calendar_sync_attempts = job.attempts
                    db.commit()
                    return

                patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
                if not patient:
                    job.status = "FAILED"
                    job.last_error = "Patient not found"
                    appointment.calendar_sync_status = "FAILED"
                    appointment.calendar_sync_last_error = job.last_error
                    appointment.calendar_sync_attempts = job.attempts
                    appointment.calendar_sync_next_attempt_at = None
                    db.commit()
                    return

                if not appointment.google_calendar_event_id:
                    event_id = self._calendar_service.create_event(
                        doctor_email=appointment.doctor_email,
                        patient_name=patient.name,
                        appointment_date=appointment.date,
                        start_time=appointment.start_time,
                        end_time=appointment.end_time,
                        description=f"Appointment with {patient.name}",
                        timezone_name=appointment.timezone
                    )
                    if event_id:
                        appointment.google_calendar_event_id = event_id
                        appointment.calendar_sync_status = "SYNCED"
                        appointment.calendar_sync_attempts = job.attempts
                        appointment.calendar_sync_next_attempt_at = None
                        appointment.calendar_sync_last_error = None
                        job.status = "COMPLETED"
                        db.commit()
                        return
                    job.last_error = "Calendar event creation failed"
                else:
                    updated = self._calendar_service.update_event(
                        doctor_email=appointment.doctor_email,
                        event_id=appointment.google_calendar_event_id,
                        patient_name=patient.name,
                        appointment_date=appointment.date,
                        start_time=appointment.start_time,
                        end_time=appointment.end_time,
                        description=f"Appointment with {patient.name}",
                        timezone_name=appointment.timezone
                    )
                    if updated:
                        appointment.calendar_sync_status = "SYNCED"
                        appointment.calendar_sync_attempts = job.attempts
                        appointment.calendar_sync_next_attempt_at = None
                        appointment.calendar_sync_last_error = None
                        job.status = "COMPLETED"
                        db.commit()
                        return
                    job.last_error = "Calendar event update failed"

            if job.action == "DELETE":
                if appointment.google_calendar_event_id:
                    self._calendar_service.delete_event(
                        doctor_email=appointment.doctor_email,
                        event_id=appointment.google_calendar_event_id
                    )
                appointment.calendar_sync_status = "SYNCED"
                appointment.calendar_sync_attempts = job.attempts
                appointment.calendar_sync_next_attempt_at = None
                appointment.calendar_sync_last_error = None
                job.status = "COMPLETED"
                db.commit()
                return

            # Retry or fail
            job.status = "PENDING"
            if not job.last_error:
                job.last_error = "Calendar sync failed"
            appointment.calendar_sync_last_error = job.last_error
            appointment.calendar_sync_attempts = job.attempts
            job.next_attempt_at = datetime.now(timezone.utc) + self._retry_delay(job.attempts)
            appointment.calendar_sync_next_attempt_at = job.next_attempt_at
            if job.attempts >= self._max_retries:
                job.status = "FAILED"
                appointment.calendar_sync_status = "FAILED"
                appointment.calendar_sync_attempts = job.attempts
                appointment.calendar_sync_next_attempt_at = None
            db.commit()
        except Exception as e:
            db.rollback()
            try:
                job = db.query(CalendarSyncJob).filter(CalendarSyncJob.id == job_id).first()
                appointment = None
                if job:
                    appointment = db.query(Appointment).filter(Appointment.id == job.appointment_id).first()
                    job.status = "PENDING"
                    job.last_error = str(e)
                    job.next_attempt_at = datetime.now(timezone.utc) + self._retry_delay(job.attempts)
                    if appointment:
                        appointment.calendar_sync_last_error = job.last_error
                        appointment.calendar_sync_next_attempt_at = job.next_attempt_at
                        appointment.calendar_sync_attempts = job.attempts
                    if job.attempts >= self._max_retries:
                        job.status = "FAILED"
                        if appointment:
                            appointment.calendar_sync_status = "FAILED"
                    db.commit()
            except Exception:
                db.rollback()
            logger.error(f"Calendar sync job failed: {e}")
        finally:
            db.close()

    def _retry_delay(self, attempts: int) -> timedelta:
        delay = self._retry_base * (2 ** max(attempts - 1, 0))
        return timedelta(seconds=delay)


calendar_sync_queue = CalendarSyncQueue()
