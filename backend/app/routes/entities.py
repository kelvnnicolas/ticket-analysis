from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..database import get_db
from ..models import SLAPolicy, Agent, Category, Customer, Ticket
from ..services.sla import evaluate_ticket

router = APIRouter(tags=["entities"])


def _paginate(skip: int, limit: int) -> tuple[int, int]:
    page_size = min(max(limit, 1), settings.max_page_size)
    page = max(skip // page_size + 1, 1)
    return page, page_size


@router.get("/customers", response_model=list[schemas.CustomerBase])
def read_customers(
    skip: int = 0,
    limit: int = Query(default=100, le=settings.max_page_size),
    db: Session = Depends(get_db),
):
    page, page_size = _paginate(skip, limit)
    return db.scalars(
        select(Customer).order_by(Customer.id).offset((page - 1) * page_size).limit(page_size)
    ).all()


@router.get("/agents", response_model=list[schemas.AgentBase])
def read_agents(
    skip: int = 0,
    limit: int = Query(default=100, le=settings.max_page_size),
    active_only: bool = False,
    db: Session = Depends(get_db),
):
    page, page_size = _paginate(skip, limit)
    stmt = select(Agent).order_by(Agent.id)
    if active_only:
        stmt = stmt.where(Agent.active == 1)
    return db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()


@router.get("/categories", response_model=list[schemas.CategoryBase])
def read_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.id)).all()


@router.get("/sla-policies", response_model=list[schemas.SLAPolicyBase])
def read_sla_policies(db: Session = Depends(get_db)):
    return db.scalars(
        select(SLAPolicy).order_by(SLAPolicy.max_resolution_time_hours)
    ).all()


@router.get("/entities/counts", tags=["entities"])
def entity_counts(db: Session = Depends(get_db)) -> dict:
    return {
        "tickets": db.scalar(select(func.count()).select_from(Ticket)) or 0,
        "customers": db.scalar(select(func.count()).select_from(Customer)) or 0,
        "agents": db.scalar(select(func.count()).select_from(Agent)) or 0,
        "categories": db.scalar(select(func.count()).select_from(Category)) or 0,
        "sla_policies": db.scalar(select(func.count()).select_from(SLAPolicy)) or 0,
    }


@router.get("/agents/{agent_id}/workload", tags=["agents"])
def agent_workload(agent_id: int, db: Session = Depends(get_db)):
    """Carga e desempenho por agente (base para o dashboard operacional)."""
    agent = db.get(Agent, agent_id)
    if agent is None:
        return {"agent_id": agent_id, "error": "agent not found"}

    _total, tickets = crud.list_tickets(
        db, schemas.TicketFilterParams(agent_id=agent_id), page=1, page_size=200
    )
    resolved = [t for t in tickets if t.resolution_time_hours is not None]
    hours = [float(t.resolution_time_hours) for t in resolved]

    return {
        "agent_id": agent.id,
        "agent": agent.name,
        "tickets_handled": len(tickets),
        "open_tickets": sum(1 for t in tickets if t.status not in ("Resolved", "Closed")),
        "breached_tickets": sum(
            1 for t in tickets if evaluate_ticket(t).sla_breached is True
        ),
        "avg_resolution_time_hours": round(sum(hours) / len(hours), 2) if hours else None,
    }