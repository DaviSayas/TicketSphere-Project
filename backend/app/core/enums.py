"""Enumerations used across models, schemas, and business logic."""
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    TECH = "tech"
    USER = "user"


class TicketStatus(str, Enum):
    OPEN = "open"               # Aberto
    ASSIGNED = "assigned"        # Atribuído
    IN_PROGRESS = "in_progress"  # Em Curso
    AWAITING = "awaiting"        # Aguarda Resposta
    RESOLVED = "resolved"        # Resolvido
    REOPENED = "reopened"        # Reaberto
    CLOSED = "closed"            # Fechado


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketSource(str, Enum):
    WEB = "web"
    EMAIL = "email"


class SlaStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"   # > 75% do prazo decorrido
    BREACHED = "breached"  # prazo ultrapassado


# State machine — chaves são estado actual, valores são transições permitidas
ALLOWED_TRANSITIONS = {
    TicketStatus.OPEN:        {TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, TicketStatus.CLOSED},
    TicketStatus.ASSIGNED:    {TicketStatus.IN_PROGRESS, TicketStatus.OPEN, TicketStatus.CLOSED},
    TicketStatus.IN_PROGRESS: {TicketStatus.AWAITING, TicketStatus.RESOLVED, TicketStatus.ASSIGNED, TicketStatus.CLOSED},
    TicketStatus.AWAITING:    {TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.CLOSED},
    TicketStatus.RESOLVED:    {TicketStatus.CLOSED, TicketStatus.REOPENED},
    TicketStatus.REOPENED:    {TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, TicketStatus.CLOSED},
    TicketStatus.CLOSED:      set(),  # estado terminal
}


def is_valid_transition(current: TicketStatus, new: TicketStatus) -> bool:
    """Check whether a status transition is allowed by the state machine."""
    if current == new:
        return False
    return new in ALLOWED_TRANSITIONS.get(current, set())
