"""Admin-only endpoints: dashboard metrics, CSV report, and soft-delete trash."""
import csv
import io
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_admin
from app.core.enums import TicketStatus
from app.db.session import get_db
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.common import (
    CategoryDistribution,
    DailySeriesPoint,
    DashboardCard,
    DashboardResponse,
    TopTech,
)
from app.schemas.ticket import TicketListItem
from app.schemas.user import UserOut
from app.services.sla import compute_sla_status

router = APIRouter(prefix="/admin", tags=["admin"])


def _ensure_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.get("/dashboard", response_model=DashboardResponse, summary="Métricas dashboard (30d)")
def dashboard(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=30)

    # ----- Cards -----
    open_tickets = (
        db.query(func.count(Ticket.id))
        .filter(Ticket.status.in_([
            TicketStatus.OPEN.value,
            TicketStatus.IN_PROGRESS.value,
            TicketStatus.AWAITING.value,
        ]))
        .scalar() or 0
    )

    recent = (
        db.query(Ticket)
        .options(joinedload(Ticket.assignee), joinedload(Ticket.category))
        .filter(Ticket.created_at >= since)
        .all()
    )

    resolved_recent = [t for t in recent if t.resolved_at is not None]
    sla_breached_recent = sum(1 for t in recent if t.sla_breached)

    if resolved_recent:
        total_seconds = sum(
            (_ensure_aware(t.resolved_at) - _ensure_aware(t.created_at)).total_seconds()
            for t in resolved_recent
        )
        avg_hours = round(total_seconds / len(resolved_recent) / 3600, 1)
    else:
        avg_hours = 0.0

    cards = DashboardCard(
        open_tickets=open_tickets,
        resolved_last_30d=len(resolved_recent),
        sla_breached_last_30d=sla_breached_recent,
        avg_resolution_hours=avg_hours,
    )

    # ----- Daily series -----
    created_by_day: dict[str, int] = defaultdict(int)
    resolved_by_day: dict[str, int] = defaultdict(int)
    for t in recent:
        created_by_day[_ensure_aware(t.created_at).strftime("%Y-%m-%d")] += 1
        if t.resolved_at:
            resolved_by_day[_ensure_aware(t.resolved_at).strftime("%Y-%m-%d")] += 1

    daily_series = []
    for i in range(30):
        day = (now - timedelta(days=29 - i)).strftime("%Y-%m-%d")
        daily_series.append(
            DailySeriesPoint(
                date=day, created=created_by_day.get(day, 0), resolved=resolved_by_day.get(day, 0)
            )
        )

    # ----- Top techs -----
    tech_stats: dict[int, dict] = {}
    for t in recent:
        if t.resolved_at and t.assignee_id:
            s = tech_stats.setdefault(
                t.assignee_id,
                {"name": t.assignee.name if t.assignee else "?", "resolved": 0, "total_h": 0.0, "breached": 0},
            )
            s["resolved"] += 1
            s["total_h"] += (
                _ensure_aware(t.resolved_at) - _ensure_aware(t.created_at)
            ).total_seconds() / 3600
            if t.sla_breached:
                s["breached"] += 1

    top_techs = []
    for uid, s in sorted(tech_stats.items(), key=lambda kv: kv[1]["resolved"], reverse=True)[:5]:
        avg_h = round(s["total_h"] / s["resolved"], 1) if s["resolved"] else 0.0
        compliance = (
            round((s["resolved"] - s["breached"]) / s["resolved"] * 100, 1)
            if s["resolved"] else 100.0
        )
        top_techs.append(
            TopTech(
                user_id=uid, name=s["name"], resolved=s["resolved"],
                avg_resolution_hours=avg_h, sla_compliance_pct=compliance,
            )
        )

    # ----- Category distribution -----
    cat_counts: dict[str, int] = defaultdict(int)
    for t in recent:
        cat_counts[t.category.name if t.category else "Sem categoria"] += 1
    category_distribution = [
        CategoryDistribution(category=k, count=v)
        for k, v in sorted(cat_counts.items(), key=lambda kv: kv[1], reverse=True)
    ]

    return DashboardResponse(
        cards=cards,
        daily_series=daily_series,
        top_techs=top_techs,
        category_distribution=category_distribution,
    )


@router.get("/reports/monthly", summary="Relatório mensal CSV")
def monthly_report(
    month: Optional[str] = Query(
        None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM. Default: mês actual."
    ),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    now = datetime.now(timezone.utc)
    if month:
        year, mon = month.split("-")
        start = datetime(int(year), int(mon), 1, tzinfo=timezone.utc)
    else:
        start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)

    tickets = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.creator),
            joinedload(Ticket.assignee),
            joinedload(Ticket.category),
        )
        .filter(Ticket.created_at >= start, Ticket.created_at < end)
        .order_by(Ticket.id)
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "titulo", "prioridade", "categoria", "criador",
        "tecnico", "criado", "resolvido", "estado", "sla_status",
    ])
    for t in tickets:
        writer.writerow([
            t.id,
            t.title,
            t.priority,
            t.category.name if t.category else "",
            t.creator.name if t.creator else "",
            t.assignee.name if t.assignee else "",
            _ensure_aware(t.created_at).isoformat(),
            _ensure_aware(t.resolved_at).isoformat() if t.resolved_at else "",
            t.status,
            compute_sla_status(t).value,
        ])

    buf.seek(0)
    filename = f"relatorio_{start.strftime('%Y-%m')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============================================================
# TRASH — soft delete / restore / permanent delete
# ============================================================

def _ticket_to_list_item(ticket: Ticket) -> TicketListItem:
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


# ---------- Trash: list ----------

@router.get("/trash/tickets", response_model=List[TicketListItem], summary="Tickets removidos (lixeira)")
def trash_list_tickets(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    tickets = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.creator),
            joinedload(Ticket.assignee),
            joinedload(Ticket.category),
        )
        .filter(Ticket.deleted_at.isnot(None))
        .order_by(Ticket.deleted_at.desc())
        .all()
    )
    return [_ticket_to_list_item(t) for t in tickets]


@router.get("/trash/users", response_model=List[UserOut], summary="Utilizadores removidos (lixeira)")
def trash_list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return db.query(User).filter(User.active == False).order_by(User.id).all()  # noqa: E712


# ---------- Soft delete ----------

@router.delete("/tickets/{ticket_id}", summary="Mover ticket para a lixeira (soft delete)")
def soft_delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.deleted_at.is_(None)).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    ticket.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "ticket_id": ticket_id}


@router.delete("/users/{user_id}", summary="Desativar utilizador (soft delete)")
def soft_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Não pode remover a sua própria conta")
    user = db.query(User).filter(User.id == user_id, User.active == True).first()  # noqa: E712
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado ou já inactivo")
    user.active = False
    db.commit()
    return {"ok": True, "user_id": user_id}


# ---------- Restore ----------

@router.post("/trash/tickets/{ticket_id}/restore", summary="Restaurar ticket da lixeira")
def restore_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.deleted_at.isnot(None)).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado na lixeira")
    ticket.deleted_at = None
    db.commit()
    return {"ok": True, "ticket_id": ticket_id}


@router.post("/trash/users/{user_id}/restore", summary="Restaurar utilizador da lixeira")
def restore_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id, User.active == False).first()  # noqa: E712
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado na lixeira")
    user.active = True
    db.commit()
    return {"ok": True, "user_id": user_id}


# ---------- Permanent delete ----------

@router.delete("/trash/tickets/{ticket_id}/permanent", summary="Apagar ticket permanentemente")
def hard_delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.deleted_at.isnot(None)).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado na lixeira")
    db.delete(ticket)
    db.commit()
    return {"ok": True, "ticket_id": ticket_id}


@router.delete("/trash/users/{user_id}/permanent", summary="Apagar utilizador permanentemente")
def hard_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Não pode apagar a sua própria conta")
    user = db.query(User).filter(User.id == user_id, User.active == False).first()  # noqa: E712
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado na lixeira")
    db.delete(user)
    db.commit()
    return {"ok": True, "user_id": user_id}
