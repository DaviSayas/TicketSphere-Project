"""Ticket endpoints — list, create, detail, state transitions, assign, comments."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, require_tech_or_admin
from app.core.enums import (
    SlaStatus,
    TicketPriority,
    TicketSource,
    TicketStatus,
    UserRole,
    is_valid_transition,
)
from app.db.session import get_db
from app.models.comment import Comment, TicketHistory
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import (
    CommentCreate,
    CommentOut,
    HistoryOut,
    PaginatedTickets,
    TicketAssignUpdate,
    TicketCreate,
    TicketDetail,
    TicketListItem,
    TicketStatusUpdate,
)
from app.services import email as email_svc
from app.services.sla import calculate_deadline, compute_sla_status, get_resolution_hours

router = APIRouter(prefix="/tickets", tags=["tickets"])


# ---------- Helpers ----------

def _to_list_item(ticket: Ticket) -> TicketListItem:
    return TicketListItem(
        id=ticket.id,
        title=ticket.title,
        status=ticket.status,
        priority=ticket.priority,
        category_id=ticket.category_id,
        category_name=ticket.category.name if ticket.category else None,
        creator_id=ticket.creator_id,
        creator_name=ticket.creator.name if ticket.creator else None,
        assignee_id=ticket.assignee_id,
        assignee_name=ticket.assignee.name if ticket.assignee else None,
        source=ticket.source,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        sla_deadline=ticket.sla_deadline,
        sla_status=compute_sla_status(ticket),
    )


def _to_detail(ticket: Ticket, viewer: User) -> TicketDetail:
    base = _to_list_item(ticket)
    comments = [
        CommentOut(
            id=c.id,
            ticket_id=c.ticket_id,
            user_id=c.user_id,
            user_name=c.user.name if c.user else None,
            body=c.body,
            is_internal=c.is_internal,
            created_at=c.created_at,
        )
        for c in ticket.comments
        # Internal comments hidden from the original requester (non-tech/admin)
        if (not c.is_internal) or viewer.role in (UserRole.ADMIN.value, UserRole.TECH.value)
    ]
    history = [
        HistoryOut(
            id=h.id,
            user_id=h.user_id,
            user_name=h.user.name if h.user else "Sistema",
            field=h.field,
            old_value=h.old_value,
            new_value=h.new_value,
            changed_at=h.changed_at,
        )
        for h in ticket.history
    ]
    return TicketDetail(
        **base.model_dump(),
        description=ticket.description,
        resolved_at=ticket.resolved_at,
        comments=comments,
        history=history,
    )


def _can_view_ticket(ticket: Ticket, user: User) -> bool:
    if user.role in (UserRole.ADMIN.value, UserRole.TECH.value):
        return True
    return ticket.creator_id == user.id


def _record_history(db: Session, ticket: Ticket, user_id: Optional[int], field: str, old, new):
    db.add(
        TicketHistory(
            ticket_id=ticket.id,
            user_id=user_id,
            field=field,
            old_value=str(old) if old is not None else None,
            new_value=str(new) if new is not None else None,
        )
    )


def _ticket_query_with_joins(db: Session):
    return db.query(Ticket).options(
        joinedload(Ticket.creator),
        joinedload(Ticket.assignee),
        joinedload(Ticket.category),
    )


# ---------- List ----------

@router.get("", response_model=PaginatedTickets, summary="Listar tickets com filtros")
def list_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: Optional[TicketStatus] = Query(None, alias="status"),
    priority: Optional[TicketPriority] = None,
    category_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    q: Optional[str] = Query(None, description="texto livre (title/description)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    only_mine: bool = False,
):
    query = _ticket_query_with_joins(db).filter(Ticket.deleted_at.is_(None))

    # Visibility filter — utilizador comum só vê os seus
    if current_user.role == UserRole.USER.value:
        query = query.filter(Ticket.creator_id == current_user.id)
    elif only_mine:
        # Tech/admin opting in to "only assigned to me"
        query = query.filter(Ticket.assignee_id == current_user.id)

    if status_filter:
        query = query.filter(Ticket.status == status_filter.value)
    if priority:
        query = query.filter(Ticket.priority == priority.value)
    if category_id is not None:
        query = query.filter(Ticket.category_id == category_id)
    if assignee_id is not None:
        query = query.filter(Ticket.assignee_id == assignee_id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Ticket.title.ilike(like), Ticket.description.ilike(like)))

    total = query.count()
    items = (
        query.order_by(Ticket.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedTickets(
        items=[_to_list_item(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------- Create ----------

@router.post(
    "",
    response_model=TicketDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Criar ticket via formulário web",
)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res_hours = get_resolution_hours(db, payload.priority.value)
    now = datetime.now(timezone.utc)

    # Auto-assign from category if defined
    assignee_id = None
    if payload.category_id:
        from app.models.category import Category
        cat = db.query(Category).filter(Category.id == payload.category_id).first()
        if cat and cat.auto_assign_to_user_id:
            assignee_id = cat.auto_assign_to_user_id

    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        status=TicketStatus.OPEN.value,
        priority=payload.priority.value,
        category_id=payload.category_id,
        creator_id=current_user.id,
        assignee_id=assignee_id,
        source=TicketSource.WEB.value,
        created_at=now,
        updated_at=now,
        sla_deadline=calculate_deadline(now, res_hours),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    _record_history(db, ticket, current_user.id, "status", None, ticket.status)
    if assignee_id:
        _record_history(db, ticket, current_user.id, "assignee", None, assignee_id)
    db.commit()

    # Notify the assignee, if any (synchronous, errors are swallowed in email_svc)
    if ticket.assignee:
        email_svc.notify_ticket_created(ticket, ticket.assignee.email)

    # Reload with relations
    ticket = _ticket_query_with_joins(db).filter(Ticket.id == ticket.id).first()
    return _to_detail(ticket, current_user)


# ---------- Detail ----------

@router.get("/{ticket_id}", response_model=TicketDetail, summary="Detalhe do ticket")
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = (
        _ticket_query_with_joins(db)
        .options(joinedload(Ticket.comments).joinedload(Comment.user))
        .options(joinedload(Ticket.history).joinedload(TicketHistory.user))
        .filter(Ticket.id == ticket_id)
        .first()
    )
    if not ticket or ticket.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    if not _can_view_ticket(ticket, current_user):
        raise HTTPException(status_code=403, detail="Sem acesso a este ticket")
    return _to_detail(ticket, current_user)


# ---------- State transitions ----------

@router.put("/{ticket_id}/status", response_model=TicketDetail, summary="Transição de estado")
def update_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tech_or_admin),
):
    ticket = _ticket_query_with_joins(db).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")

    # Tech can only edit tickets they're assigned to (or unassigned ones); admin can edit all
    if current_user.role == UserRole.TECH.value:
        if ticket.assignee_id and ticket.assignee_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Apenas o técnico atribuído pode alterar este ticket"
            )

    current = TicketStatus(ticket.status)
    new = payload.status
    if not is_valid_transition(current, new):
        raise HTTPException(
            status_code=400,
            detail=f"Transição inválida: {current.value} → {new.value}",
        )

    old_value = ticket.status
    ticket.status = new.value
    if new == TicketStatus.RESOLVED:
        ticket.resolved_at = datetime.now(timezone.utc)
    elif new == TicketStatus.REOPENED:
        ticket.resolved_at = None

    _record_history(db, ticket, current_user.id, "status", old_value, new.value)
    db.commit()
    db.refresh(ticket)

    # Notify creator on resolution
    if new == TicketStatus.RESOLVED and ticket.creator and ticket.creator.email:
        email_svc.notify_ticket_resolved(ticket, ticket.creator.email)

    ticket = _ticket_query_with_joins(db).filter(Ticket.id == ticket.id).first()
    return _to_detail(ticket, current_user)


# ---------- Assign ----------

@router.put("/{ticket_id}/assign", response_model=TicketDetail, summary="Atribuir/desatribuir técnico")
def assign_ticket(
    ticket_id: int,
    payload: TicketAssignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tech_or_admin),
):
    ticket = _ticket_query_with_joins(db).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")

    new_assignee = None
    if payload.assignee_id is not None:
        new_assignee = (
            db.query(User)
            .filter(
                User.id == payload.assignee_id,
                User.active == True,  # noqa: E712
                User.role.in_(["tech", "admin"]),
            )
            .first()
        )
        if not new_assignee:
            raise HTTPException(status_code=400, detail="Técnico inválido")

    old = ticket.assignee_id
    ticket.assignee_id = payload.assignee_id
    _record_history(
        db, ticket, current_user.id, "assignee", old, payload.assignee_id
    )
    db.commit()
    db.refresh(ticket)

    if new_assignee:
        email_svc.notify_ticket_assigned(ticket, new_assignee.email)

    ticket = _ticket_query_with_joins(db).filter(Ticket.id == ticket.id).first()
    return _to_detail(ticket, current_user)


# ---------- Comments ----------

@router.post(
    "/{ticket_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar comentário",
)
def add_comment(
    ticket_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = (
        _ticket_query_with_joins(db).filter(Ticket.id == ticket_id).first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    if not _can_view_ticket(ticket, current_user):
        raise HTTPException(status_code=403, detail="Sem acesso a este ticket")

    # Only tech/admin can post internal comments
    is_internal = payload.is_internal and current_user.role in (
        UserRole.TECH.value,
        UserRole.ADMIN.value,
    )

    comment = Comment(
        ticket_id=ticket.id,
        user_id=current_user.id,
        body=payload.body,
        is_internal=is_internal,
    )
    db.add(comment)
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(comment)

    # Notify creator if this is a public comment from a tech/admin
    if (
        not is_internal
        and current_user.id != ticket.creator_id
        and ticket.creator
        and ticket.creator.email
    ):
        email_svc.notify_new_comment(ticket, ticket.creator.email, payload.body)

    return CommentOut(
        id=comment.id,
        ticket_id=comment.ticket_id,
        user_id=comment.user_id,
        user_name=current_user.name,
        body=comment.body,
        is_internal=comment.is_internal,
        created_at=comment.created_at,
    )
