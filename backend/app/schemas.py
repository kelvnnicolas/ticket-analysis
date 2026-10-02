from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import STATUSES

TicketStatus = Literal["New", "Assigned", "In Progress", "Resolved", "Closed"]
Priority = Literal["Low", "Medium", "High"]

PositiveInt = Annotated[int, Field(gt=0)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Entidades
# --------------------------------------------------------------------------- #


class CustomerBase(ORMModel):
    id: int
    name: str
    email: str


class AgentBase(ORMModel):
    id: int
    name: str
    email: str
    active: int = 1


class CategoryBase(ORMModel):
    id: int
    name: str
    description: Optional[str] = None


class SLAPolicyBase(ORMModel):
    id: int
    priority: str
    max_resolution_time_hours: float


class TicketStatusHistoryBase(ORMModel):
    id: int
    ticket_id: int
    status: str
    changed_at: datetime
    changed_by_agent_id: Optional[int] = None
    note: Optional[str] = None


# --------------------------------------------------------------------------- #
# SLA
# --------------------------------------------------------------------------- #


class SLAInfo(ORMModel):
    priority: Optional[str] = None
    sla_limit_hours: Optional[float] = None
    sla_due_at: Optional[datetime] = None
    elapsed_hours: float = 0.0
    remaining_hours: Optional[float] = None
    sla_state: str
    sla_breached: Optional[bool] = None


# --------------------------------------------------------------------------- #
# Tickets
# --------------------------------------------------------------------------- #


class TicketBase(ORMModel):
    issue_type: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    operating_system: Optional[str] = Field(default=None, max_length=50)
    category_id: PositiveInt
    customer_id: Optional[PositiveInt] = None
    agent_id: Optional[PositiveInt] = None
    sla_policy_id: Optional[PositiveInt] = None
    status: TicketStatus = "New"


class TicketCreate(TicketBase):
    """Criação aceita ``priority`` como atalho para resolução da política SLA."""

    priority: Optional[Priority] = None


class TicketUpdate(ORMModel):
    status: Optional[TicketStatus] = None
    agent_id: Optional[PositiveInt] = None
    category_id: Optional[PositiveInt] = None
    sla_policy_id: Optional[PositiveInt] = None
    description: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=500)


class TicketResponse(TicketBase):
    id: int
    date_opened: datetime
    date_resolved: Optional[datetime] = None
    resolution_time_hours: Optional[float] = None

    customer: Optional[CustomerBase] = None
    agent: Optional[AgentBase] = None
    category: CategoryBase
    sla_policy: Optional[SLAPolicyBase] = None
    sla: Optional[SLAInfo] = None


class TicketSummary(ORMModel):
    """Listagem enxuta, sem joins de relacionamento."""

    id: int
    issue_type: str
    category: str
    agent: Optional[str] = None
    status: str
    date_opened: datetime
    resolution_time_hours: Optional[float] = None
    sla_state: str
    sla_due_at: Optional[datetime] = None


class TicketListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TicketSummary]


class TicketFilterParams(ORMModel):
    status: Optional[str] = None
    category_id: Optional[int] = None
    agent_id: Optional[int] = None
    customer_id: Optional[int] = None
    priority: Optional[str] = None
    sla_state: Optional[str] = None
    search: Optional[str] = None
    opened_from: Optional[datetime] = None
    opened_to: Optional[datetime] = None
    sort_by: str = "date_opened"
    sort_dir: str = "desc"
    #: Instante de referência para avaliar o SLA dos tickets abertos.
    reference_time: Optional[datetime] = None


VALID_SLA_STATES = frozenset(
    {"met", "breached", "on_track", "at_risk", "no_policy"}
)
VALID_SORT_FIELDS = frozenset(
    {
        "id",
        "date_opened",
        "date_resolved",
        "status",
        "issue_type",
        "resolution_time_hours",
    }
)

__all__ = [
    "AgentBase",
    "CategoryBase",
    "CustomerBase",
    "PRIORITIES",
    "STATUSES",
    "SLAInfo",
    "SLAPolicyBase",
    "TicketBase",
    "TicketCreate",
    "TicketFilterParams",
    "TicketListResponse",
    "TicketResponse",
    "TicketStatusHistoryBase",
    "TicketSummary",
    "TicketUpdate",
    "VALID_SLA_STATES",
    "VALID_SORT_FIELDS",
]

PRIORITIES = ("Low", "Medium", "High")