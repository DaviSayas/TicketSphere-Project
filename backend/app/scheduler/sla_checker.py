"""Background job: scan open tickets, flag SLA breaches, send alerts."""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import joinedload

from app.core.enums import TicketStatus
from app.db.session import SessionLocal
from app.models.ticket import Ticket
from app.services import email as email_svc

logger = logging.getLogger(__name__)

OPEN_STATUSES = [
    TicketStatus.OPEN.value,
    TicketStatus.ASSIGNED.value,
    TicketStatus.IN_PROGRESS.value,
    TicketStatus.AWAITING.value,
    TicketStatus.REOPENED.value,
]


def check_sla_once() -> int:
    """Mark newly-breached tickets, notify, return count flagged."""
    db = SessionLocal()
    flagged = 0
    try:
        now = datetime.now(timezone.utc)

        candidates = (
            db.query(Ticket)
            .options(joinedload(Ticket.assignee), joinedload(Ticket.creator))
            .filter(
                Ticket.status.in_(OPEN_STATUSES),
                Ticket.sla_breached == False,  # noqa: E712
                Ticket.sla_deadline.isnot(None),
            )
            .all()
        )

        for ticket in candidates:
            deadline = ticket.sla_deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            if now >= deadline:
                ticket.sla_breached = True
                flagged += 1
                recipients = []
                if ticket.assignee and ticket.assignee.email:
                    recipients.append(ticket.assignee.email)
                # Also notify admins
                from app.models.user import User
                admins = (
                    db.query(User).filter(User.role == "admin", User.active == True).all()  # noqa: E712
                )
                for a in admins:
                    if a.email and a.email not in recipients:
                        recipients.append(a.email)
                email_svc.notify_sla_breach(ticket, recipients)

        if flagged:
            db.commit()
            logger.info("SLA checker: flagged %d ticket(s) as breached", flagged)
    finally:
        db.close()

    return flagged
