"""Initialise database: create tables and load seed data.

Usage:
    python -m app.db.seed
"""
import logging
from datetime import datetime, timedelta, timezone

from app.core.enums import TicketPriority, TicketSource, TicketStatus, UserRole
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import Category, Comment, SlaPolicy, Ticket, TicketHistory, User
from app.services.sla import calculate_deadline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created (or already existed)")


def seed():
    db = SessionLocal()
    try:
        # ---------- SLA policies (per priority) ----------
        sla_defaults = [
            (TicketPriority.URGENT.value, 1, 4),
            (TicketPriority.HIGH.value, 2, 8),
            (TicketPriority.MEDIUM.value, 4, 24),
            (TicketPriority.LOW.value, 8, 72),
        ]
        for prio, resp, res in sla_defaults:
            if not db.query(SlaPolicy).filter(SlaPolicy.priority == prio).first():
                db.add(SlaPolicy(priority=prio, response_hours=resp, resolution_hours=res))
        db.commit()
        logger.info("SLA policies seeded")

        # ---------- Users ----------
        users_data = [
            ("Administrador", "admin@empresa.pt", "admin123", UserRole.ADMIN.value),
            ("Técnico", "tecnico@empresa.pt", "tecnico123", UserRole.TECH.value),
            ("Técnico 2", "tecnico2@empresa.pt", "tecnico123", UserRole.TECH.value),
            ("Técnico 3", "tecnico3@empresa.pt", "tecnico123", UserRole.TECH.value),
            ("Utilizador", "utilizador@empresa.pt", "user123", UserRole.USER.value),
            ("Utilizador 2", "utilizador2@empresa.pt", "user123", UserRole.USER.value),
        ]
        users = {}
        for name, email, pw, role in users_data:
            u = db.query(User).filter(User.email == email).first()
            if not u:
                u = User(
                    name=name,
                    email=email,
                    hashed_password=hash_password(pw),
                    role=role,
                    active=True,
                )
                db.add(u)
            users[email] = u
        db.commit()
        for u in users.values():
            db.refresh(u)
        logger.info("Users seeded (%d)", len(users))

        # ---------- Categories ----------
        cats_data = [
            ("Hardware", 24, users["tecnico@empresa.pt"].id),
            ("Software", 12, users["tecnico2@empresa.pt"].id),
            ("Rede", 8, users["tecnico3@empresa.pt"].id),
            ("Acesso", 4, None),
            ("Outro", 48, None),
        ]
        cats = {}
        for name, sla_h, assignee_id in cats_data:
            c = db.query(Category).filter(Category.name == name).first()
            if not c:
                c = Category(
                    name=name, default_sla_hours=sla_h, auto_assign_to_user_id=assignee_id
                )
                db.add(c)
            cats[name] = c
        db.commit()
        for c in cats.values():
            db.refresh(c)
        logger.info("Categories seeded (%d)", len(cats))

        # ---------- Tickets (only if empty) ----------
        if db.query(Ticket).count() > 0:
            logger.info("Tickets already exist — skipping ticket seed")
            return

        now = datetime.now(timezone.utc)
        sample_tickets = [
            # (title, description, priority, category, status, creator_email, assignee_email, days_ago)
            ("Monitor não liga", "O monitor do PC do balcão deixou de ligar esta manhã.",
             TicketPriority.HIGH.value, "Hardware", TicketStatus.OPEN.value,
             "utilizador@empresa.pt", "tecnico@empresa.pt", 1),
            ("Não consigo aceder ao Outlook", "Mensagem de erro 'credenciais inválidas' mesmo depois de mudar password.",
             TicketPriority.MEDIUM.value, "Software", TicketStatus.IN_PROGRESS.value,
             "utilizador2@empresa.pt", "tecnico2@empresa.pt", 2),
            ("WiFi muito lenta na sala de reuniões 3",
             "A ligação cai constantemente durante chamadas Teams.",
             TicketPriority.MEDIUM.value, "Rede", TicketStatus.AWAITING.value,
             "utilizador@empresa.pt", "tecnico3@empresa.pt", 3),
            ("Pedido de acesso ao SharePoint", "Preciso de acesso à pasta 'RH 2025'.",
             TicketPriority.LOW.value, "Acesso", TicketStatus.RESOLVED.value,
             "utilizador2@empresa.pt", "tecnico2@empresa.pt", 5),
            ("Servidor principal em baixo!!!", "Toda a equipa está sem acesso a ficheiros partilhados.",
             TicketPriority.URGENT.value, "Rede", TicketStatus.RESOLVED.value,
             "utilizador@empresa.pt", "tecnico@empresa.pt", 7),
            ("Impressora floor 2 com erro PC-LOAD-LETTER",
             "Não imprime nada. Mensagem estranha no LCD.",
             TicketPriority.LOW.value, "Hardware", TicketStatus.OPEN.value,
             "utilizador2@empresa.pt", None, 0),
            ("Reset password VPN", "Esqueci a password do cliente VPN.",
             TicketPriority.MEDIUM.value, "Acesso", TicketStatus.CLOSED.value,
             "utilizador@empresa.pt", "tecnico3@empresa.pt", 10),
            ("Sugestão: 2º monitor", "Seria útil ter segundo monitor para programação.",
             TicketPriority.LOW.value, "Outro", TicketStatus.OPEN.value,
             "utilizador2@empresa.pt", None, 4),
            ("Software de contabilidade não abre",
             "Aplicação trava no splash screen desde a actualização de Windows.",
             TicketPriority.HIGH.value, "Software", TicketStatus.IN_PROGRESS.value,
             "utilizador@empresa.pt", "tecnico2@empresa.pt", 1),
            ("Cabo de rede partido", "Cabo Ethernet sob a secretária está danificado.",
             TicketPriority.MEDIUM.value, "Hardware", TicketStatus.RESOLVED.value,
             "utilizador2@empresa.pt", "tecnico@empresa.pt", 6),
        ]

        for (title, desc, prio, cat_name, status, creator_email, assignee_email, days_ago) in sample_tickets:
            from app.services.sla import get_resolution_hours
            res_hours = get_resolution_hours(db, prio)
            created_at = now - timedelta(days=days_ago, hours=2)
            resolved_at = None
            if status in (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value):
                resolved_at = created_at + timedelta(hours=min(res_hours, 6))

            ticket = Ticket(
                title=title,
                description=desc,
                status=status,
                priority=prio,
                category_id=cats[cat_name].id,
                creator_id=users[creator_email].id,
                assignee_id=users[assignee_email].id if assignee_email else None,
                source=TicketSource.WEB.value,
                created_at=created_at,
                updated_at=created_at,
                resolved_at=resolved_at,
                sla_deadline=calculate_deadline(created_at, res_hours),
                sla_breached=False,
            )
            db.add(ticket)
            db.flush()  # need ID for history

            db.add(TicketHistory(
                ticket_id=ticket.id,
                user_id=ticket.creator_id,
                field="status",
                old_value=None,
                new_value=TicketStatus.OPEN.value,
                changed_at=created_at,
            ))
            if assignee_email:
                db.add(TicketHistory(
                    ticket_id=ticket.id, user_id=ticket.creator_id, field="assignee",
                    old_value=None, new_value=str(ticket.assignee_id), changed_at=created_at,
                ))
            if status != TicketStatus.OPEN.value:
                db.add(TicketHistory(
                    ticket_id=ticket.id, user_id=ticket.assignee_id, field="status",
                    old_value=TicketStatus.OPEN.value, new_value=status,
                    changed_at=created_at + timedelta(hours=2),
                ))

        db.commit()
        logger.info("Sample tickets seeded (%d)", len(sample_tickets))

    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed()
    print("✅ Base de dados inicializada com sucesso!")
