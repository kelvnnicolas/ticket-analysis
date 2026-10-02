import pytest

from backend.app.services import lifecycle


def test_canonical_flow_is_allowed():
    assert lifecycle.can_transition("New", "Assigned")
    assert lifecycle.can_transition("Assigned", "In Progress")
    assert lifecycle.can_transition("In Progress", "Resolved")
    assert lifecycle.can_transition("Resolved", "Closed")


def test_skip_forward_from_new_is_allowed():
    assert lifecycle.can_transition("New", "In Progress")
    assert lifecycle.can_transition("New", "Closed")


def test_reopen_from_closed_is_allowed():
    assert lifecycle.can_transition("Closed", "In Progress")
    assert "In Progress" in lifecycle.allowed_transitions("Closed")


def test_invalid_transition_raises():
    with pytest.raises(ValueError, match="Invalid transition"):
        lifecycle.validate_transition("Closed", "Assigned")


def test_unknown_status_raises():
    with pytest.raises(ValueError, match="Unknown status"):
        lifecycle.validate_transition("New", "Bogus")


def test_resolving_statuses_drive_resolution_stamp():
    from backend.app import models

    assert frozenset(models.RESOLVING_STATUSES) == frozenset({"Resolved", "Closed"})


def test_reopening_statuses_detected():
    # Reabertura devolve o ticket a um estado aberto; 'Closed' a partir de
    # 'Resolved' é encerramento normal, não reabertura.
    assert lifecycle.REOPENING_STATUSES == frozenset({"In Progress"})