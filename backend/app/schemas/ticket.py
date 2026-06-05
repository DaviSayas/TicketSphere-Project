"""Pydantic schemas for tickets, comments, history."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import SlaStatus, TicketPriority, TicketSource, TicketStatus


# ---------- Comments ----------

class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)
    is_internal: bool = False


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    user_id: int
    user_name: Optional[str] = None
    body: str
    is_internal: bool
    created_at: datetime


# ---------- History ----------

class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_at: datetime


# ---------- Tickets ----------

class TicketCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(default="", max_length=10000)
    priority: TicketPriority = TicketPriority.MEDIUM
    category_id: Optional[int] = None


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketAssignUpdate(BaseModel):
    assignee_id: Optional[int] = None  # None unassigns


class TicketListItem(BaseModel):
    """Slim shape used in list endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: str
    priority: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    creator_id: int
    creator_name: Optional[str] = None
    assignee_id: Optional[int] = None
    assignee_name: Optional[str] = None
    source: str
    created_at: datetime
    updated_at: datetime
    sla_deadline: Optional[datetime] = None
    sla_status: SlaStatus = SlaStatus.OK


class TicketDetail(TicketListItem):
    """Full ticket including description, comments, history."""
    description: str
    resolved_at: Optional[datetime] = None
    comments: List[CommentOut] = []
    history: List[HistoryOut] = []


class PaginatedTickets(BaseModel):
    items: List[TicketListItem]
    total: int
    page: int
    page_size: int
