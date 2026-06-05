"""SLA helper unit tests."""
from datetime import datetime, timedelta, timezone

from app.core.enums import SlaStatus, TicketStatus
from app.services.sla import calculate_deadline, compute_sla_status


class _FakeTicket:
    def __init__(self, status, created_at, sla_deadline, sla_breached=False):
        self.status = status
        self.created_at = created_at
        self.sla_deadline = sla_deadline
        self.sla_breached = sla_breached


def test_calculate_deadline():
    base = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert calculate_deadline(base, 24) == base + timedelta(hours=24)


def test_sla_ok_when_plenty_of_time():
    now = datetime.now(timezone.utc)
    t = _FakeTicket(
        TicketStatus.OPEN.value,
        created_at=now - timedelta(hours=1),
        sla_deadline=now + timedelta(hours=23),
    )
    assert compute_sla_status(t) == SlaStatus.OK


def test_sla_warning_above_75_percent():
    now = datetime.now(timezone.utc)
    # 80% elapsed of a 10h window
    t = _FakeTicket(
        TicketStatus.OPEN.value,
        created_at=now - timedelta(hours=8),
        sla_deadline=now + timedelta(hours=2),
    )
    assert compute_sla_status(t) == SlaStatus.WARNING


def test_sla_breached_past_deadline():
    now = datetime.now(timezone.utc)
    t = _FakeTicket(
        TicketStatus.OPEN.value,
        created_at=now - timedelta(hours=10),
        sla_deadline=now - timedelta(hours=1),
    )
    assert compute_sla_status(t) == SlaStatus.BREACHED


def test_resolved_ticket_uses_persisted_flag():
    now = datetime.now(timezone.utc)
    t = _FakeTicket(
        TicketStatus.RESOLVED.value,
        created_at=now - timedelta(days=5),
        sla_deadline=now - timedelta(days=4),
        sla_breached=False,
    )
    # Even though deadline passed, resolved + not-flagged = OK
    assert compute_sla_status(t) == SlaStatus.OK
