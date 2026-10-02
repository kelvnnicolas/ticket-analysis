"""Motor de SLA (V4).

Calcula, para cada ticket, o prazo de resolução (``sla_due_at``) a partir da
política vinculada à prioridade, e classifica o atendimento em três estados
operacionais:

* ``met``      - resolvido dentro do prazo
* ``breached`` - resolvido após o prazo
* ``open``     - ainda não resolvido; retorna também o quanto falta (ou o
                 atraso acumulado) em horas
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from ..config import utcnow
from ..models import OPEN_STATUSES

ON_TRACK_THRESHOLD_RATIO = 0.8


@dataclass(frozen=True)
class SLAEvaluation:
    priority: str | None
    sla_limit_hours: float | None
    sla_due_at: datetime | None
    elapsed_hours: float
    remaining_hours: float | None
    sla_state: str
    sla_breached: bool | None

    def as_dict(self) -> dict:
        return asdict(self)


def sla_limit_hours(sla_policy) -> float | None:
    if sla_policy is None or sla_policy.max_resolution_time_hours is None:
        return None
    return float(sla_policy.max_resolution_time_hours)


def sla_due_at(date_opened: datetime, limit_hours: float | None) -> datetime | None:
    if limit_hours is None:
        return None
    return date_opened + timedelta(hours=limit_hours)


def evaluate_ticket(
    ticket, reference_time: datetime | None = None
) -> SLAEvaluation:
    """Avalia o SLA de um ticket. ``reference_time`` existe para testes."""
    reference = reference_time or utcnow()
    limit = sla_limit_hours(ticket.sla_policy)
    priority = ticket.sla_policy.priority if ticket.sla_policy else None

    opened_at = ticket.date_opened
    end = ticket.date_resolved or reference
    elapsed = max((end - opened_at).total_seconds() / 3600.0, 0.0)

    due = sla_due_at(opened_at, limit)

    if ticket.status in OPEN_STATUSES:
        remaining = None if limit is None else limit - elapsed
        breached: bool | None = None
        if remaining is None:
            state = "no_policy"
        elif remaining < 0:
            state = "breached"
            breached = True
        elif elapsed >= limit * ON_TRACK_THRESHOLD_RATIO:
            state = "at_risk"
        else:
            state = "on_track"
    else:
        remaining = None
        if limit is None:
            state = "no_policy"
        else:
            breached = elapsed > limit
            state = "breached" if breached else "met"

    return SLAEvaluation(
        priority=priority,
        sla_limit_hours=limit,
        sla_due_at=due,
        elapsed_hours=round(elapsed, 2),
        remaining_hours=None if remaining is None else round(remaining, 2),
        sla_state=state,
        sla_breached=breached,
    )


def is_overdue(ticket, reference_time: datetime | None = None) -> bool:
    evaluation = evaluate_ticket(ticket, reference_time)
    return evaluation.sla_state == "breached"


def sla_state_expression(reference_time: datetime | None = None):
    """Equivalente SQL de :func:`evaluate_ticket`, para filtragem no banco.

    Requer ``JOIN`` com ``sla_policies``. Mantém a semântica em paridade com a
    avaliação em memória para que listagens e contagens não divergam.
    """
    from sqlalchemy import case, func

    from .. import models

    reference = reference_time or utcnow()
    limit = models.SLAPolicy.max_resolution_time_hours
    is_open = models.Ticket.status.in_(OPEN_STATUSES)

    open_elapsed = func.extract("epoch", reference - models.Ticket.date_opened) / 3600.0
    closed_elapsed = func.coalesce(models.Ticket.resolution_time_hours, open_elapsed)
    elapsed = case((is_open, open_elapsed), else_=closed_elapsed)

    return case(
        (limit.is_(None), "no_policy"),
        (is_open & (elapsed > limit), "breached"),
        (is_open & (elapsed >= limit * ON_TRACK_THRESHOLD_RATIO), "at_risk"),
        (is_open, "on_track"),
        (elapsed > limit, "breached"),
        else_="met",
    )


def sla_due_at_expression():
    """``date_opened + limite da política`` como expressão SQL."""
    from sqlalchemy import Float, cast, func

    from .. import models

    limit = cast(models.SLAPolicy.max_resolution_time_hours, Float) * 3600.0
    return models.Ticket.date_opened + func.make_interval(secs=limit)