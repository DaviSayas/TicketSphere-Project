"""IMAP polling — reads unread messages from the support mailbox and creates tickets.

This module is intentionally defensive: malformed emails, decoding errors, or HTML
without text fallback should never crash the polling loop.
"""
import email
import imaplib
import logging
from email.header import decode_header, make_header
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import TicketPriority, TicketSource, TicketStatus
from app.db.session import SessionLocal
from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.services.sla import calculate_deadline, get_resolution_hours

logger = logging.getLogger(__name__)

PROCESSED_FOLDER = "Processado"


def _decode(value) -> str:
    """Decode an RFC-2047 encoded email header safely."""
    if value is None:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:  # noqa: BLE001
        return str(value)


def _extract_body(msg: email.message.Message) -> str:
    """Pull plain text out of an email message, falling back gracefully to HTML."""
    if msg.is_multipart():
        # Prefer text/plain
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if ctype == "text/plain" and "attachment" not in disp.lower():
                try:
                    payload = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
                except Exception:  # noqa: BLE001
                    continue
        # Fall back to first text/html stripped of tags
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                try:
                    payload = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    raw = payload.decode(charset, errors="replace")
                    # Crude tag strip; good enough for ticket description
                    import re
                    return re.sub(r"<[^>]+>", " ", raw)
                except Exception:  # noqa: BLE001
                    continue
        return ""
    # Single-part
    try:
        payload = msg.get_payload(decode=True) or b""
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def _find_or_create_email_creator(db: Session, from_addr: str) -> User:
    """Find a user matching the email's From, or fall back to a generic system user."""
    if from_addr:
        user = db.query(User).filter(User.email == from_addr).first()
        if user:
            return user
    # Generic catch-all user for email-only senders
    generic = db.query(User).filter(User.email == "email-inbound@local").first()
    if not generic:
        from app.core.security import hash_password
        generic = User(
            name="Email Inbound",
            email="email-inbound@local",
            hashed_password=hash_password("disabled-account"),
            role="user",
            active=False,  # cannot login
        )
        db.add(generic)
        db.commit()
        db.refresh(generic)
    return generic


def _parse_sender(raw_from: str) -> str:
    """Extract just the email address out of 'Name <addr@host>' formats."""
    if not raw_from:
        return ""
    if "<" in raw_from and ">" in raw_from:
        return raw_from.split("<", 1)[1].split(">", 1)[0].strip().lower()
    return raw_from.strip().lower()


def _ensure_processed_folder(mail: imaplib.IMAP4) -> None:
    """Create the Processado folder if it doesn't exist. Silently ignore failures."""
    try:
        mail.create(PROCESSED_FOLDER)
    except Exception:  # noqa: BLE001
        pass


def poll_inbox_once() -> int:
    """Connect to IMAP, fetch unread messages, create tickets. Returns count created."""
    created = 0
    try:
        if settings.IMAP_USE_SSL:
            mail = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT)
        else:
            mail = imaplib.IMAP4(settings.IMAP_HOST, settings.IMAP_PORT)
        mail.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
    except Exception as e:  # noqa: BLE001
        logger.warning("IMAP connection failed (%s) — skipping this poll", e)
        return 0

    try:
        mail.select("INBOX")
        _ensure_processed_folder(mail)

        status, data = mail.search(None, "UNSEEN")
        if status != "OK":
            logger.warning("IMAP search returned status %s", status)
            return 0

        ids: List[bytes] = data[0].split() if data and data[0] else []
        if not ids:
            return 0

        db: Session = SessionLocal()
        try:
            for msg_id in ids:
                try:
                    if _process_message(mail, msg_id, db):
                        created += 1
                except Exception as e:  # noqa: BLE001
                    logger.error("Failed to process message %s: %s", msg_id, e)
        finally:
            db.close()
    finally:
        try:
            mail.logout()
        except Exception:  # noqa: BLE001
            pass

    if created:
        logger.info("IMAP poll: created %d ticket(s) from email", created)
    return created


def _process_message(mail: imaplib.IMAP4, msg_id: bytes, db: Session) -> bool:
    """Fetch a single message, create a ticket, move it to Processado. Returns True on success."""
    status, msg_data = mail.fetch(msg_id, "(RFC822)")
    if status != "OK" or not msg_data or not msg_data[0]:
        return False

    raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
    msg = email.message_from_bytes(raw)

    subject = _decode(msg.get("Subject")) or "(sem assunto)"
    from_addr = _parse_sender(_decode(msg.get("From")))
    body = _extract_body(msg).strip()

    creator = _find_or_create_email_creator(db, from_addr)

    # Auto-categorise: very simple keyword heuristic — first matching category, else None
    category = _guess_category(db, subject + " " + body)

    priority = TicketPriority.MEDIUM.value
    res_hours = get_resolution_hours(db, priority)

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    ticket = Ticket(
        title=subject[:200],
        description=body[:10000],
        status=TicketStatus.OPEN.value,
        priority=priority,
        category_id=category.id if category else None,
        creator_id=creator.id,
        assignee_id=category.auto_assign_to_user_id if category else None,
        source=TicketSource.EMAIL.value,
        created_at=now,
        updated_at=now,
        sla_deadline=calculate_deadline(now, res_hours),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Mark seen + move to Processado folder
    try:
        mail.store(msg_id, "+FLAGS", "\\Seen")
        mail.copy(msg_id, PROCESSED_FOLDER)
        mail.store(msg_id, "+FLAGS", "\\Deleted")
        mail.expunge()
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not move processed message: %s", e)

    return True


def _guess_category(db: Session, text: str) -> Optional[Category]:
    """Very small keyword heuristic to bucket inbound emails."""
    text_lower = text.lower()
    keywords = {
        "Hardware": ["hardware", "pc", "monitor", "teclado", "rato", "impressora"],
        "Software": ["software", "aplicação", "programa", "instalar", "erro"],
        "Rede": ["rede", "wifi", "internet", "vpn", "conexão"],
        "Acesso": ["password", "acesso", "login", "conta", "permissão"],
    }
    for cat_name, words in keywords.items():
        if any(w in text_lower for w in words):
            cat = db.query(Category).filter(Category.name == cat_name).first()
            if cat:
                return cat
    return db.query(Category).filter(Category.name == "Outro").first()
