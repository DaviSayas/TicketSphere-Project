"""SLA business logic: deadline calculation and on-the-fly status."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.enums import SlaStatus, TicketPriority, TicketStatus
from app.models.sla import SlaPolicy
from app.models.ticket import Ticket


# Fallback hours per priority if no SlaPolicy row is found
DEFAULT_RESOLUTION_HOURS = {
    TicketPriority.URGENT.value: 4,
    TicketPriority.HIGH.value: 8,
    TicketPriority.MEDIUM.value: 24,
    TicketPriority.LOW.value: 72,
}


def _ensure_aware(dt: datetime) -> datetime:
    """Coerce naive datetimes (SQLite default) into UTC-aware ones."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_resolution_hours(db: Session, priority: str) -> int:
    """Look up resolution_hours for a priority, falling back to defaults."""
    policy = db.query(SlaPolicy).filter(SlaPolicy.priority == priority).first()
    if policy:
        return policy.resolution_hours
    return DEFAULT_RESOLUTION_HOURS.get(priority, 24)


def calculate_deadline(created_at: datetime, resolution_hours: int) -> datetime:
    """sla_deadline = created_at + resolution_hours."""
    return _ensure_aware(created_at) + timedelta(hours=resolution_hours)


def compute_sla_status(ticket: Ticket) -> SlaStatus:
    """On-the-fly SLA status: ok / warning (>75% elapsed) / breached.

    Resolved or closed tickets always report ok unless they were breached at resolution.
    """
    # Terminal states use the persisted flag
    if ticket.status in (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value):
        return SlaStatus.BREACHED if ticket.sla_breached else SlaStatus.OK

    if ticket.sla_deadline is None:
        return SlaStatus.OK

    now = datetime.now(timezone.utc)
    deadline = _ensure_aware(ticket.sla_deadline)
    created = _ensure_aware(ticket.created_at)

    if now >= deadline:
        return SlaStatus.BREACHED

    total = (deadline - created).total_seconds()
    elapsed = (now - created).total_seconds()
    if total <= 0:
        return SlaStatus.OK

    pct = elapsed / total
    if pct >= 0.75:
        return SlaStatus.WARNING
    return SlaStatus.OK
