from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base

NEW = "New"
ASSIGNED = "Assigned"
IN_PROGRESS = "In Progress"
RESOLVED = "Resolved"
CLOSED = "Closed"

STATUSES: tuple[str, ...] = (NEW, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED)
OPEN_STATUSES: tuple[str, ...] = (NEW, ASSIGNED, IN_PROGRESS)
RESOLVING_STATUSES: tuple[str, ...] = (RESOLVED, CLOSED)
TERMINAL_STATUSES: tuple[str, ...] = (RESOLVED, CLOSED)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)

    tickets = relationship("Ticket", back_populates="customer")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    active = Column(Integer, nullable=False, default=1)

    tickets = relationship("Ticket", back_populates="agent")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

    tickets = relationship("Ticket", back_populates="category")


class SLAPolicy(Base):
    __tablename__ = "sla_policies"

    id = Column(Integer, primary_key=True, index=True)
    priority = Column(String(20), unique=True, nullable=False)
    max_resolution_time_hours = Column(Numeric(8, 2), nullable=False)

    tickets = relationship("Ticket", back_populates="sla_policy")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    sla_policy_id = Column(Integer, ForeignKey("sla_policies.id"))
    issue_type = Column(String(100), nullable=False)
    description = Column(Text)
    operating_system = Column(String(50))
    status = Column(String(20), nullable=False, default="New", index=True)
    date_opened = Column(DateTime, nullable=False, index=True)
    date_resolved = Column(DateTime)
    resolution_time_hours = Column(Numeric(10, 2))

    customer = relationship("Customer", back_populates="tickets")
    agent = relationship("Agent", back_populates="tickets")
    category = relationship("Category", back_populates="tickets")
    sla_policy = relationship("SLAPolicy", back_populates="tickets")
    history = relationship(
        "TicketStatusHistory",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketStatusHistory.changed_at",
    )

    __table_args__ = (
        CheckConstraint("status <> ''", name="ck_tickets_status_not_empty"),
    )


class TicketStatusHistory(Base):
    __tablename__ = "ticket_status_history"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(String(20), nullable=False)
    changed_at = Column(DateTime, nullable=False)
    changed_by_agent_id = Column(Integer, ForeignKey("agents.id"))
    note = Column(Text)

    ticket = relationship("Ticket", back_populates="history")
    changed_by_agent = relationship("Agent")

    __table_args__ = (
        CheckConstraint("status <> ''", name="ck_history_status_not_empty"),
    )