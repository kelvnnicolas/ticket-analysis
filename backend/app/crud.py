from datetime import datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from . import models, schemas
from .config import utcnow
from .services import lifecycle
from .services.sla import sla_state_expression


class NotFoundError(Exception):
    """Entidade referenciada não existe."""


class ConflictError(Exception):
    """Operação conflita com o estado atual do recurso."""


# --------------------------------------------------------------------------- #
# Leitura
# --------------------------------------------------------------------------- #


def get_ticket(db: Session, ticket_id: int) -> models.Ticket | None:
    return db.get(models.Ticket, ticket_id)


def get_ticket_or_raise(db: Session, ticket_id: int) -> models.Ticket:
    ticket = get_ticket(db, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    return ticket


def _apply_filters(stmt: Select, params: schemas.TicketFilterParams) -> Select:
    if params.status:
        stmt = stmt.where(models.Ticket.status == params.status)
    if params.category_id:
        stmt = stmt.where(models.Ticket.category_id == params.category_id)
    if params.agent_id:
        stmt = stmt.where(models.Ticket.agent_id == params.agent_id)
    if params.customer_id:
        stmt = stmt.where(models.Ticket.customer_id == params.customer_id)
    if params.priority or params.sla_state:
        stmt = stmt.join(models.SLAPolicy, models.Ticket.sla_policy_id == models.SLAPolicy.id)
    if params.priority:
        stmt = stmt.where(models.SLAPolicy.priority == params.priority)
    if params.sla_state:
        stmt = stmt.where(
            sla_state_expression(params.reference_time) == params.sla_state
        )
    if params.opened_from:
        stmt = stmt.where(models.Ticket.date_opened >= params.opened_from)
    if params.opened_to:
        stmt = stmt.where(models.Ticket.date_opened <= params.opened_to)
    if params.search:
        pattern = f"%{params.search.strip()}%"
        stmt = stmt.where(
            or_(
                models.Ticket.issue_type.ilike(pattern),
                models.Ticket.description.ilike(pattern),
                models.Ticket.operating_system.ilike(pattern),
            )
        )
    return stmt


def list_tickets(
    db: Session,
    params: schemas.TicketFilterParams | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[int, list[models.Ticket]]:
    params = params or schemas.TicketFilterParams()

    total = db.scalar(
        _apply_filters(select(func.count()).select_from(models.Ticket), params)
    )

    sort_column = getattr(models.Ticket, params.sort_by, models.Ticket.date_opened)
    ordering = (
        sort_column.desc() if params.sort_dir.lower() == "desc" else sort_column.asc()
    )
    stmt = (
        _apply_filters(select(models.Ticket), params)
        .order_by(ordering)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(
            selectinload(models.Ticket.category),
            selectinload(models.Ticket.agent),
            selectinload(models.Ticket.customer),
            selectinload(models.Ticket.sla_policy),
        )
    )

    rows = db.scalars(stmt).all()
    return int(total or 0), list(rows)


def get_ticket_history(db: Session, ticket_id: int) -> list[models.TicketStatusHistory]:
    return list(
        db.scalars(
            select(models.TicketStatusHistory)
            .where(models.TicketStatusHistory.ticket_id == ticket_id)
            .order_by(models.TicketStatusHistory.changed_at.asc())
        )
    )


# --------------------------------------------------------------------------- #
# Escrita
# --------------------------------------------------------------------------- #


def resolve_sla_policy_id(
    db: Session, priority: str | None, sla_policy_id: int | None
) -> int | None:
    """Resolve a política SLA por id explícito ou por prioridade."""
    if sla_policy_id is not None:
        policy = db.get(models.SLAPolicy, sla_policy_id)
        if policy is None:
            raise NotFoundError(f"SLA policy {sla_policy_id} not found")
        return policy.id

    if priority is None:
        return None

    policy = db.scalar(select(models.SLAPolicy).where(models.SLAPolicy.priority == priority))
    if policy is None:
        raise NotFoundError(f"No SLA policy configured for priority '{priority}'")
    return policy.id


def _record_history(
    db: Session,
    ticket: models.Ticket,
    status: str,
    changed_at: datetime,
    agent_id: int | None = None,
    note: str | None = None,
) -> models.TicketStatusHistory:
    entry = models.TicketStatusHistory(
        ticket_id=ticket.id,
        status=status,
        changed_at=changed_at,
        changed_by_agent_id=agent_id,
        note=note,
    )
    db.add(entry)
    return entry


def create_ticket(db: Session, payload: schemas.TicketCreate) -> models.Ticket:
    now = utcnow()
    data = payload.model_dump(exclude={"priority"})

    data["sla_policy_id"] = resolve_sla_policy_id(
        db, payload.priority, payload.sla_policy_id
    )

    for fk_field, model in (
        ("category_id", models.Category),
        ("agent_id", models.Agent),
        ("customer_id", models.Customer),
    ):
        if data.get(fk_field) is not None and db.get(model, data[fk_field]) is None:
            raise NotFoundError(f"{model.__name__.lower()} {data[fk_field]} not found")

    ticket = models.Ticket(**data, date_opened=now)
    db.add(ticket)
    db.flush()
    _record_history(db, ticket, ticket.status, now, agent_id=payload.agent_id)
    db.commit()
    return get_ticket_or_raise(db, ticket.id)


def update_ticket(
    db: Session, ticket_id: int, payload: schemas.TicketUpdate
) -> models.Ticket:
    ticket = get_ticket_or_raise(db, ticket_id)
    data = payload.model_dump(exclude_unset=True, exclude={"note"})

    if "sla_policy_id" in data and data["sla_policy_id"] is not None:
        if db.get(models.SLAPolicy, data["sla_policy_id"]) is None:
            raise NotFoundError(f"SLA policy {data['sla_policy_id']} not found")

    if "agent_id" in data and data["agent_id"] is not None:
        if db.get(models.Agent, data["agent_id"]) is None:
            raise NotFoundError(f"Agent {data['agent_id']} not found")

    if "category_id" in data and data["category_id"] is not None:
        if db.get(models.Category, data["category_id"]) is None:
            raise NotFoundError(f"Category {data['category_id']} not found")

    now = utcnow()
    status_changed = False

    if "status" in data and data["status"] is not None:
        target = data["status"]
        if target != ticket.status:
            try:
                lifecycle.validate_transition(ticket.status, target)
            except ValueError as exc:
                raise ConflictError(str(exc)) from exc

            if (
                target in lifecycle.RESOLVING_STATUSES
                and ticket.status not in lifecycle.RESOLVING_STATUSES
            ):
                ticket.date_resolved = now
                ticket.resolution_time_hours = round(
                    (now - ticket.date_opened).total_seconds() / 3600.0, 2
                )
            elif (
                ticket.status in lifecycle.RESOLVING_STATUSES
                and target not in lifecycle.RESOLVING_STATUSES
            ):
                ticket.date_resolved = None
                ticket.resolution_time_hours = None

            ticket.status = target
            status_changed = True

    for key, value in data.items():
        if key != "status":
            setattr(ticket, key, value)

    db.flush()

    if status_changed:
        _record_history(
            db,
            ticket,
            ticket.status,
            now,
            agent_id=ticket.agent_id,
            note=payload.note,
        )

    db.commit()
    return get_ticket_or_raise(db, ticket.id)


def delete_ticket(db: Session, ticket_id: int) -> None:
    ticket = get_ticket(db, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    if ticket.status not in lifecycle.RESOLVING_STATUSES:
        raise ConflictError(
            f"Ticket {ticket_id} is '{ticket.status}'. "
            "Only Resolved or Closed tickets can be deleted."
        )
    db.delete(ticket)
    db.commit()