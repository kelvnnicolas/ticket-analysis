"""Regras de transição do ciclo de vida do ticket (V4).

O fluxo canônico é:

    New -> Assigned -> In Progress -> Resolved -> Closed

Reabertura é permitida a partir de ``Resolved``/``Closed`` (retorno para
``In Progress``) porque é uma necessidade operacional comum em ITSM.
"""

from ..models import (
    ASSIGNED,
    CLOSED,
    IN_PROGRESS,
    NEW,
    OPEN_STATUSES,
    RESOLVED,
    RESOLVING_STATUSES,
    STATUSES,
)

TRANSITIONS: dict[str, tuple[str, ...]] = {
    NEW: (ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED),
    ASSIGNED: (IN_PROGRESS, RESOLVED, CLOSED, NEW),
    IN_PROGRESS: (RESOLVED, CLOSED, ASSIGNED),
    RESOLVED: (CLOSED, IN_PROGRESS),
    CLOSED: (IN_PROGRESS,),
}

#: Transições que reabrem um ticket já resolvido/fechado, devolvendo-o a um
#: estado aberto (``Closed`` a partir de ``Resolved`` é encerramento normal).
REOPENING_STATUSES = frozenset(
    target
    for source, targets in TRANSITIONS.items()
    if source in RESOLVING_STATUSES
    for target in targets
    if target in OPEN_STATUSES
)


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, ())


def allowed_transitions(current: str) -> list[str]:
    return list(TRANSITIONS.get(current, ()))


def validate_transition(current: str, target: str) -> None:
    """Levanta ``ValueError`` se a transição não for permitida."""
    if target not in STATUSES:
        raise ValueError(f"Unknown status '{target}'. Valid: {', '.join(STATUSES)}")
    if not can_transition(current, target):
        raise ValueError(
            f"Invalid transition '{current}' -> '{target}'. "
            f"Allowed from '{current}': "
            f"{', '.join(allowed_transitions(current)) or 'none (terminal state)'}"
        )