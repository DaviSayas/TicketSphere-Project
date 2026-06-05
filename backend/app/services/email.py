"""Email sending service. Templates are simple .html files with {placeholders}."""
import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _load_template(name: str) -> str:
    path = TEMPLATES_DIR / name
    if not path.exists():
        logger.warning("Email template %s not found at %s", name, path)
        return "<p>{body}</p>"
    return path.read_text(encoding="utf-8")


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an email via SMTP. Failures are logged and return False, never raise."""
    if not to:
        logger.warning("send_email called with empty 'to'; skipping.")
        return False

    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content("Este email requer um cliente compatível com HTML.")
    msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as s:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                s.starttls()
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:  # noqa: BLE001 — broad catch is intentional (don't break business flow)
        logger.error("Failed to send email to %s: %s", to, e)
        return False


def render(template_name: str, **kwargs) -> str:
    """Render a template by replacing {placeholders} with str(kwargs)."""
    tpl = _load_template(template_name)
    # Use str.format_map with a defaulting dict so missing keys don't raise
    class _Defaulting(dict):
        def __missing__(self, key):
            return ""
    return tpl.format_map(_Defaulting(kwargs))


# ---------- Convenience wrappers for ticket events ----------

def notify_ticket_created(ticket, assignee_email: Optional[str]):
    if not assignee_email:
        return
    body = render(
        "ticket_assigned.html",
        ticket_id=ticket.id,
        title=ticket.title,
        priority=ticket.priority,
        description=ticket.description[:500],
    )
    send_email(assignee_email, f"[Ticket #{ticket.id}] Atribuído: {ticket.title}", body)


def notify_ticket_assigned(ticket, assignee_email: str):
    body = render(
        "ticket_assigned.html",
        ticket_id=ticket.id,
        title=ticket.title,
        priority=ticket.priority,
        description=ticket.description[:500],
    )
    send_email(assignee_email, f"[Ticket #{ticket.id}] Atribuído: {ticket.title}", body)


def notify_new_comment(ticket, creator_email: str, comment_body: str):
    body = render(
        "new_comment.html",
        ticket_id=ticket.id,
        title=ticket.title,
        comment=comment_body[:1000],
    )
    send_email(creator_email, f"[Ticket #{ticket.id}] Novo comentário", body)


def notify_ticket_resolved(ticket, creator_email: str):
    body = render(
        "ticket_resolved.html",
        ticket_id=ticket.id,
        title=ticket.title,
    )
    send_email(creator_email, f"[Ticket #{ticket.id}] Resolvido: {ticket.title}", body)


def notify_sla_breach(ticket, recipients: list[str]):
    body = render(
        "sla_breach.html",
        ticket_id=ticket.id,
        title=ticket.title,
        priority=ticket.priority,
        deadline=ticket.sla_deadline.isoformat() if ticket.sla_deadline else "",
    )
    for r in recipients:
        if r:
            send_email(r, f"[ALERTA SLA] Ticket #{ticket.id} excedeu o prazo", body)
