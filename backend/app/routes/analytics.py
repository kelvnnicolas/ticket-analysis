import json
import os

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import (
    OPEN_STATUSES,
    RESOLVING_STATUSES,
    STATUSES,
    Agent,
    Category,
    SLAPolicy,
    Ticket,
    TicketStatusHistory,
)
from ..services.sla import evaluate_ticket

router = APIRouter(prefix="/analytics", tags=["analytics"])

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
_METRICS_PATH = os.path.join(_PROJECT_ROOT, "analytics", "outputs", "dashboard_metrics.json")

TICKETS_LOAD = (
    selectinload(Ticket.category),
    selectinload(Ticket.agent),
    selectinload(Ticket.sla_policy),
)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(int(round((pct / 100) * (len(ordered) - 1))), len(ordered) - 1)
    return ordered[index]


def _all_tickets(db: Session) -> list[Ticket]:
    return list(db.scalars(select(Ticket).options(*TICKETS_LOAD)).all())


def _first_response_hours(db: Session) -> dict[int, float]:
    """FRT por ticket: New -> In Progress, usando o histórico."""
    rows = db.execute(
        select(
            TicketStatusHistory.ticket_id,
            TicketStatusHistory.status,
            func.min(TicketStatusHistory.changed_at),
        )
        .where(TicketStatusHistory.status.in_(["New", "In Progress"]))
        .group_by(TicketStatusHistory.ticket_id, TicketStatusHistory.status)
    ).all()

    opened: dict[int, float] = {}
    responded: dict[int, float] = {}
    for ticket_id, status_value, changed_at in rows:
        target = opened if status_value == "New" else responded
        target[ticket_id] = changed_at

    frt = {}
    for ticket_id, opened_at in opened.items():
        responded_at = responded.get(ticket_id)
        if responded_at is None:
            continue
        frt[ticket_id] = (responded_at - opened_at).total_seconds() / 3600.0
    return frt


@router.get("/overview")
def get_analytics_overview(db: Session = Depends(get_db)) -> dict:
    """Métricas calculadas ao vivo sobre o banco (fonte de verdade da API)."""
    tickets = _all_tickets(db)
    resolved = [t for t in tickets if t.status in RESOLVING_STATUSES]
    resolution_hours = [
        float(t.resolution_time_hours)
        for t in resolved
        if t.resolution_time_hours is not None
    ]

    frt = _first_response_hours(db)
    frt_values = list(frt.values())

    evaluations = [evaluate_ticket(t) for t in resolved]
    breached = [e for e in evaluations if e.sla_breached is True]
    met = [e for e in evaluations if e.sla_breached is False]
    without_policy = [e for e in evaluations if e.sla_state == "no_policy"]

    open_tickets = [t for t in tickets if t.status in OPEN_STATUSES]
    open_breached = [
        t for t in open_tickets if evaluate_ticket(t).sla_state == "breached"
    ]

    total_with_sla = len(met) + len(breached)
    compliance = (len(met) / total_with_sla * 100) if total_with_sla else 0.0

    return {
        "total_volume": len(tickets),
        "resolved_volume": len(resolved),
        "open_volume": len(open_tickets),
        "open_breached": len(open_breached),
        "avg_resolution_time_hrs": (
            round(sum(resolution_hours) / len(resolution_hours), 2)
            if resolution_hours
            else None
        ),
        "median_resolution_time_hrs": _median(resolution_hours),
        "p90_resolution_time_hrs": _percentile(resolution_hours, 90),
        "avg_first_response_time_hrs": (
            round(sum(frt_values) / len(frt_values), 2) if frt_values else None
        ),
        "compliance_rate_percent": round(compliance, 2),
        "breached_tickets": len(breached),
        "met_sla_tickets": len(met),
        "tickets_without_sla_policy": len(without_policy),
        "by_status": {
            value: sum(1 for t in tickets if t.status == value) for value in STATUSES
        },
    }


@router.get("/by-category")
def volume_by_category(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(
            Category.name,
            func.count(Ticket.id),
            func.avg(Ticket.resolution_time_hours),
        )
        .join(Ticket, Ticket.category_id == Category.id)
        .group_by(Category.name)
        .order_by(func.count(Ticket.id).desc())
    ).all()
    return [
        {
            "category": name,
            "tickets": count,
            "avg_resolution_time_hours": round(float(avg), 2) if avg is not None else None,
        }
        for name, count, avg in rows
    ]


@router.get("/by-priority")
def volume_by_priority(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(
            SLAPolicy.priority,
            SLAPolicy.max_resolution_time_hours,
            func.count(Ticket.id),
            func.avg(Ticket.resolution_time_hours),
        )
        .join(Ticket, Ticket.sla_policy_id == SLAPolicy.id)
        .group_by(SLAPolicy.priority, SLAPolicy.max_resolution_time_hours)
    ).all()

    return [
        {
            "priority": priority,
            "sla_limit_hours": float(limit),
            "tickets": count,
            "avg_resolution_time_hours": round(float(avg), 2) if avg is not None else None,
        }
        for priority, limit, count, avg in rows
    ]


@router.get("/by-agent")
def volume_by_agent(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(Agent.name, func.count(Ticket.id))
        .join(Ticket, Ticket.agent_id == Agent.id)
        .group_by(Agent.name)
        .order_by(func.count(Ticket.id).desc())
    ).all()
    return [{"agent": name, "tickets_handled": count} for name, count in rows]


@router.get("/sla-compliance")
def sla_compliance(db: Session = Depends(get_db)) -> list[dict]:
    """Compliance por prioridade, no formato usado pelo dashboard."""
    tickets = [
        t
        for t in _all_tickets(db)
        if t.status in RESOLVING_STATUSES and t.sla_policy is not None
    ]

    buckets: dict[str, dict] = {}
    for ticket in tickets:
        evaluation = evaluate_ticket(ticket)
        bucket = buckets.setdefault(
            evaluation.priority,
            {
                "priority": evaluation.priority,
                "sla_limit_hours": evaluation.sla_limit_hours,
                "resolved": 0,
                "met": 0,
                "breached": 0,
            },
        )
        bucket["resolved"] += 1
        if evaluation.sla_breached:
            bucket["breached"] += 1
        else:
            bucket["met"] += 1

    for bucket in buckets.values():
        bucket["compliance_rate_percent"] = round(bucket["met"] / bucket["resolved"] * 100, 2)

    return sorted(buckets.values(), key=lambda b: b["sla_limit_hours"] or 0)


@router.get("/backlog")
def backlog(db: Session = Depends(get_db)) -> dict:
    """Backlog atual: tickets abertos ordenados por urgência de SLA."""
    tickets = [t for t in _all_tickets(db) if t.status in OPEN_STATUSES]
    evaluations = [(t, evaluate_ticket(t)) for t in tickets]
    evaluations.sort(key=lambda pair: pair[1].sla_due_at or pair[0].date_opened)

    return {
        "open_count": len(tickets),
        "at_risk": sum(1 for _, e in evaluations if e.sla_state == "at_risk"),
        "breached": sum(1 for _, e in evaluations if e.sla_state == "breached"),
        "tickets": [
            {
                "id": t.id,
                "issue_type": t.issue_type,
                "status": t.status,
                "category": t.category.name if t.category else None,
                "agent": t.agent.name if t.agent else None,
                "sla_state": e.sla_state,
                "sla_due_at": e.sla_due_at,
                "remaining_hours": e.remaining_hours,
            }
            for t, e in evaluations
        ],
    }


@router.get("/trend")
def volume_trend(db: Session = Depends(get_db)) -> list[dict]:
    """Volume diário de abertura e resolução (últimos 90 dias com dados)."""
    opened = db.execute(
        select(
            func.date_trunc("day", Ticket.date_opened).label("day"),
            func.count(Ticket.id),
        ).group_by("day").order_by("day")
    ).all()

    resolved = dict(
        db.execute(
            select(
                func.date_trunc("day", Ticket.date_resolved).label("day"),
                func.count(Ticket.id),
            )
            .where(Ticket.date_resolved.isnot(None))
            .group_by("day")
        ).all()
    )

    return [
        {
            "day": day.date().isoformat() if day else None,
            "opened": count,
            "resolved": resolved.get(day, 0),
        }
        for day, count in opened
    ]


@router.get("/pipeline-report")
def pipeline_report() -> dict:
    """Métricas pré-computadas pelo pipeline Python (batch, arquivo local)."""
    try:
        with open(_METRICS_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "error": "Analytics metrics not generated yet. Run the pipeline first."
        }