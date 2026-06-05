"""APScheduler setup — IMAP polling and SLA checker."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.scheduler.sla_checker import check_sla_once
from app.services.email_ingest import poll_inbox_once

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.ENABLE_SCHEDULER:
        logger.info("Scheduler disabled (ENABLE_SCHEDULER=false)")
        return None
    if _scheduler is not None:
        return _scheduler

    sched = BackgroundScheduler(timezone="UTC", daemon=True)
    sched.add_job(
        poll_inbox_once,
        "interval",
        minutes=settings.IMAP_POLL_MINUTES,
        id="imap_poll",
        max_instances=1,
        coalesce=True,
    )
    sched.add_job(
        check_sla_once,
        "interval",
        minutes=settings.SLA_CHECK_MINUTES,
        id="sla_checker",
        max_instances=1,
        coalesce=True,
    )
    sched.start()
    _scheduler = sched
    logger.info(
        "Scheduler started: IMAP every %dm, SLA every %dm",
        settings.IMAP_POLL_MINUTES,
        settings.SLA_CHECK_MINUTES,
    )
    return sched


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
