"""
Calendar Reconcile Service - periodic Google Calendar -> DB backfill sync.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.calendar_watch import CalendarWatch
from app.models.doctor import Doctor
from app.services.calendar_sync_service import CalendarSyncService

logger = logging.getLogger(__name__)


class CalendarReconcileService:
    """Background service to backfill calendar changes when webhooks fail."""

    def __init__(self) -> None:
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._offset = 0
        self._sync_service = CalendarSyncService()

    def start(self) -> None:
        if not settings.CALENDAR_RECONCILE_ENABLED:
            logger.info("Calendar reconcile worker disabled")
            return
        if self._worker and self._worker.is_alive():
            return
        self._stop_event.clear()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()
        logger.info("Calendar reconcile worker started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._worker:
            self._worker.join(timeout=5)

    def is_running(self) -> bool:
        return bool(self._worker and self._worker.is_alive())

    def _run(self) -> None:
        interval = max(30, settings.CALENDAR_RECONCILE_INTERVAL_SECONDS)
        while not self._stop_event.is_set():
            try:
                self._reconcile_batch()
            except Exception as e:
                logger.error(f"Calendar reconcile worker error: {e}")
            self._stop_event.wait(interval)

    def _reconcile_batch(self) -> None:
        doctor_emails = self._get_next_doctor_batch()
        if not doctor_emails:
            return
        logger.info(
            "Calendar reconcile: syncing %s doctors",
            len(doctor_emails)
        )
        for doctor_email in doctor_emails:
            if self._stop_event.is_set():
                return
            self._sync_doctor(doctor_email)

    def _get_next_doctor_batch(self) -> List[str]:
        db = SessionLocal()
        try:
            doctor_query = db.query(Doctor.email).filter(Doctor.is_active == True)
            if settings.CALENDAR_RECONCILE_REQUIRE_ACTIVE_WATCH:
                doctor_query = doctor_query.join(
                    CalendarWatch,
                    CalendarWatch.doctor_email == Doctor.email
                ).filter(CalendarWatch.is_active == True)
            doctor_query = doctor_query.distinct().order_by(Doctor.email)

            total = doctor_query.count()
            if total == 0:
                return []
            if self._offset >= total:
                self._offset = 0
            batch = (
                doctor_query
                .offset(self._offset)
                .limit(settings.CALENDAR_RECONCILE_BATCH_SIZE)
                .all()
            )
            if not batch:
                self._offset = 0
                return []
            self._offset += len(batch)
            return [row[0] for row in batch]
        finally:
            db.close()

    def _sync_doctor(self, doctor_email: str) -> None:
        db = SessionLocal()
        try:
            self._run_sync(self._sync_service.sync_calendar_to_db, doctor_email, db)
            db.commit()
        except Exception as e:
            logger.error(f"Calendar reconcile failed for {doctor_email}: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()

    def _run_sync(self, coro, *args) -> None:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(coro(*args))
        finally:
            loop.close()


calendar_reconcile_service = CalendarReconcileService()
