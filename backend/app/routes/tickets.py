from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..database import get_db
from ..services import lifecycle
from ..services.sla import evaluate_ticket

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _to_summary(ticket) -> schemas.TicketSummary:
    evaluation = evaluate_ticket(ticket)
    return schemas.TicketSummary(
        id=ticket.id,
        issue_type=ticket.issue_type,
        category=ticket.category.name if ticket.category else "unknown",
        agent=ticket.agent.name if ticket.agent else None,
        status=ticket.status,
        date_opened=ticket.date_opened,
        resolution_time_hours=(
            float(ticket.resolution_time_hours)
            if ticket.resolution_time_hours is not None
            else None
        ),
        sla_state=evaluation.sla_state,
        sla_due_at=evaluation.sla_due_at,
    )


@router.get("/", response_model=schemas.TicketListResponse)
def read_tickets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    category_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    priority: Optional[str] = None,
    sla_state: Optional[str] = None,
    search: Optional[str] = None,
    opened_from: Optional[str] = None,
    opened_to: Optional[str] = None,
    sort_by: str = "date_opened",
    sort_dir: str = "desc",
    db: Session = Depends(get_db),
):
    if status_filter and status_filter not in schemas.STATUSES:
        raise HTTPException(422, f"Invalid status. Valid: {', '.join(schemas.STATUSES)}")
    if sort_by not in schemas.VALID_SORT_FIELDS:
        raise HTTPException(
            422, f"Invalid sort_by. Valid: {', '.join(sorted(schemas.VALID_SORT_FIELDS))}"
        )
    if sort_dir.lower() not in ("asc", "desc"):
        raise HTTPException(422, "sort_dir must be 'asc' or 'desc'")
    if sla_state and sla_state not in schemas.VALID_SLA_STATES:
        raise HTTPException(
            422,
            f"Invalid sla_state. Valid: {', '.join(sorted(schemas.VALID_SLA_STATES))}",
        )

    filters = schemas.TicketFilterParams(
        status=status_filter,
        category_id=category_id,
        agent_id=agent_id,
        customer_id=customer_id,
        priority=priority,
        sla_state=sla_state,
        search=search,
        opened_from=_parse_datetime(opened_from, "opened_from"),
        opened_to=_parse_datetime(opened_to, "opened_to"),
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    total, rows = crud.list_tickets(db, filters, page=page, page_size=page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_to_summary(t) for t in rows],
    }


def _parse_datetime(raw: Optional[str], field: str) -> Optional[datetime]:
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(422, f"{field} must be ISO-8601, got '{raw}'") from exc


@router.get("/{ticket_id}", response_model=schemas.TicketResponse)
def read_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = crud.get_ticket(db, ticket_id=ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    evaluation = evaluate_ticket(ticket)
    return {
        **schemas.TicketResponse.model_validate(ticket).model_dump(),
        "sla": evaluation.as_dict(),
    }


@router.get("/{ticket_id}/history", response_model=list[schemas.TicketStatusHistoryBase])
def read_ticket_history(ticket_id: int, db: Session = Depends(get_db)):
    if crud.get_ticket(db, ticket_id=ticket_id) is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return crud.get_ticket_history(db, ticket_id)


@router.get("/{ticket_id}/transitions", tags=["lifecycle"])
def read_allowed_transitions(ticket_id: int, db: Session = Depends(get_db)):
    ticket = crud.get_ticket(db, ticket_id=ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {
        "ticket_id": ticket.id,
        "current_status": ticket.status,
        "allowed": lifecycle.allowed_transitions(ticket.status),
    }


@router.get("/{ticket_id}/sla", response_model=schemas.SLAInfo)
def read_ticket_sla(ticket_id: int, db: Session = Depends(get_db)):
    ticket = crud.get_ticket(db, ticket_id=ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return evaluate_ticket(ticket).as_dict()


@router.post(
    "/", response_model=schemas.TicketResponse, status_code=status.HTTP_201_CREATED
)
def create_ticket(payload: schemas.TicketCreate, db: Session = Depends(get_db)):
    try:
        ticket = crud.create_ticket(db=db, payload=payload)
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        **schemas.TicketResponse.model_validate(ticket).model_dump(),
        "sla": evaluate_ticket(ticket).as_dict(),
    }


@router.patch("/{ticket_id}", response_model=schemas.TicketResponse)
def update_ticket(
    ticket_id: int, payload: schemas.TicketUpdate, db: Session = Depends(get_db)
):
    try:
        ticket = crud.update_ticket(db=db, ticket_id=ticket_id, payload=payload)
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except crud.ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        **schemas.TicketResponse.model_validate(ticket).model_dump(),
        "sla": evaluate_ticket(ticket).as_dict(),
    }


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    try:
        crud.delete_ticket(db=db, ticket_id=ticket_id)
    except crud.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except crud.ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc