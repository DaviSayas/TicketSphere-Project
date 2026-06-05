"""Import all models so SQLAlchemy's metadata registers them."""
from app.models.category import Category
from app.models.comment import Comment, TicketHistory
from app.models.sla import SlaPolicy
from app.models.ticket import Ticket
from app.models.user import User

__all__ = ["User", "Category", "Ticket", "Comment", "TicketHistory", "SlaPolicy"]
