from datetime import datetime, timedelta

import pytest

from backend.app import models
from backend.app.services.sla import evaluate_ticket, sla_due_at, sla_limit_hours

REFERENCE = datetime(2026, 10, 1, 12, 0, 0)


def make_ticket(seed, status="New", opened_hours_ago=0, resolution_hours=None):
    opened = REFERENCE - timedelta(hours=opened_hours_ago)
    return models.Ticket(
        id=1,
        issue_type="VPN Issue",
        category_id=seed["categories"][0].id,
        sla_policy_id=seed["policies"]["High"].id,
        status=status,
        date_opened=opened,
        date_resolved=opened + timedelta(hours=resolution_hours) if resolution_hours else None,
        resolution_time_hours=resolution_hours,
        sla_policy=seed["policies"]["High"],
    )


def test_sla_limit_and_due_date(seed):
    policy = seed["policies"]["High"]
    assert sla_limit_hours(policy) == 24.0

    opened = datetime(2026, 10, 1, 8, 0, 0)
    assert sla_due_at(opened, 24.0) == datetime(2026, 10, 2, 8, 0, 0)


def test_resolved_within_sla_is_met(seed):
    ticket = make_ticket(seed, status="Closed", resolution_hours=10)
    result = evaluate_ticket(ticket, REFERENCE)
    assert result.sla_state == "met"
    assert result.sla_breached is False
    assert result.remaining_hours is None


def test_resolved_after_sla_is_breached(seed):
    ticket = make_ticket(seed, status="Resolved", resolution_hours=30)
    result = evaluate_ticket(ticket, REFERENCE)
    assert result.sla_state == "breached"
    assert result.sla_breached is True


def test_open_ticket_on_track(seed):
    ticket = make_ticket(seed, status="New", opened_hours_ago=2)
    result = evaluate_ticket(ticket, REFERENCE)
    assert result.sla_state == "on_track"
    assert result.remaining_hours == pytest.approx(22.0)
    assert result.sla_breached is None


def test_open_ticket_at_risk(seed):
    # 80% do limite consumido (19.2h) -> at_risk
    ticket = make_ticket(seed, status="In Progress", opened_hours_ago=20)
    result = evaluate_ticket(ticket, REFERENCE)
    assert result.sla_state == "at_risk"
    assert result.remaining_hours == pytest.approx(4.0)


def test_open_ticket_overdue_is_breached(seed):
    ticket = make_ticket(seed, status="Assigned", opened_hours_ago=30)
    result = evaluate_ticket(ticket, REFERENCE)
    assert result.sla_state == "breached"
    assert result.remaining_hours == pytest.approx(-6.0)


def test_ticket_without_policy(seed):
    ticket = make_ticket(seed, status="New")
    ticket.sla_policy = None
    result = evaluate_ticket(ticket, REFERENCE)
    assert result.sla_state == "no_policy"
    assert result.sla_limit_hours is None
    assert result.sla_due_at is None