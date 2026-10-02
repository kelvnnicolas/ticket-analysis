from datetime import datetime, timedelta

from backend.app import models


def _ticket(client, **overrides):
    payload = {
        "issue_type": "VPN Issue",
        "category_id": 1,
        "priority": "High",
        "description": "Dropped connection",
    }
    payload.update(overrides)
    response = client.post("/tickets/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_resolves_sla_policy_from_priority(client, seed):
    body = _ticket(client)

    assert body["status"] == "New"
    assert body["sla_policy"]["priority"] == "High"
    assert body["sla"]["sla_limit_hours"] == 24.0
    assert body["sla"]["sla_state"] == "on_track"


def test_create_records_initial_history(client, seed):
    ticket = _ticket(client)

    history = client.get(f"/tickets/{ticket['id']}/history").json()
    assert len(history) == 1
    assert history[0]["status"] == "New"


def test_create_rejects_unknown_category(client, seed):
    response = client.post(
        "/tickets/", json={"issue_type": "X", "category_id": 999, "priority": "High"}
    )
    assert response.status_code == 422


def test_create_rejects_unknown_priority(client, seed):
    response = client.post(
        "/tickets/", json={"issue_type": "X", "category_id": 1, "priority": "Critical"}
    )
    assert response.status_code == 422


def test_get_ticket_returns_sla_block(client, seed):
    ticket = _ticket(client)

    fetched = client.get(f"/tickets/{ticket['id']}").json()
    assert fetched["id"] == ticket["id"]
    assert fetched["sla"]["priority"] == "High"


def test_get_ticket_not_found(client, seed):
    assert client.get("/tickets/4242").status_code == 404


def test_allowed_transitions_endpoint(client, seed):
    ticket = _ticket(client)

    body = client.get(f"/tickets/{ticket['id']}/transitions").json()
    assert body["current_status"] == "New"
    assert "Assigned" in body["allowed"]


def test_full_lifecycle_stamps_resolution(client, seed):
    ticket = _ticket(client)
    tid = ticket["id"]

    for status in ("Assigned", "In Progress", "Resolved"):
        response = client.patch(f"/tickets/{tid}", json={"status": status})
        assert response.status_code == 200, response.text

    body = response.json()
    assert body["status"] == "Resolved"
    assert body["date_resolved"] is not None
    assert body["resolution_time_hours"] is not None
    assert body["sla"]["sla_state"] in {"met", "breached"}


def test_reopen_clears_resolution_stamp(client, seed):
    ticket = _ticket(client)
    tid = ticket["id"]

    client.patch(f"/tickets/{tid}", json={"status": "Closed"})
    body = client.patch(f"/tickets/{tid}", json={"status": "In Progress"}).json()

    assert body["status"] == "In Progress"
    assert body["date_resolved"] is None
    assert body["resolution_time_hours"] is None


def test_invalid_transition_returns_409(client, seed):
    ticket = _ticket(client)
    tid = ticket["id"]

    client.patch(f"/tickets/{tid}", json={"status": "Closed"})
    response = client.patch(f"/tickets/{tid}", json={"status": "Assigned"})

    assert response.status_code == 409
    assert "Invalid transition" in response.json()["detail"]


def test_history_records_every_transition(client, seed):
    ticket = _ticket(client)
    tid = ticket["id"]

    client.patch(f"/tickets/{tid}", json={"status": "Assigned"})
    client.patch(f"/tickets/{tid}", json={"status": "In Progress"})

    history = client.get(f"/tickets/{tid}/history").json()
    assert [h["status"] for h in history] == ["New", "Assigned", "In Progress"]


def test_history_accepts_note(client, seed):
    ticket = _ticket(client)
    tid = ticket["id"]

    client.patch(f"/tickets/{tid}", json={"status": "Assigned", "note": "Escalado ao NOC"})
    history = client.get(f"/tickets/{tid}/history").json()

    assert history[-1]["note"] == "Escalado ao NOC"


def test_sla_endpoint_reports_open_state(client, seed):
    ticket = _ticket(client)

    body = client.get(f"/tickets/{ticket['id']}/sla").json()
    assert body["sla_state"] == "on_track"
    assert body["remaining_hours"] > 0


def test_delete_open_ticket_conflicts(client, seed):
    ticket = _ticket(client)

    assert client.delete(f"/tickets/{ticket['id']}").status_code == 409


def test_delete_closed_ticket(client, seed):
    ticket = _ticket(client)
    tid = ticket["id"]

    client.patch(f"/tickets/{tid}", json={"status": "Closed"})
    assert client.delete(f"/tickets/{tid}").status_code == 204
    assert client.get(f"/tickets/{tid}").status_code == 404


def test_list_pagination_and_filters(client, seed):
    for index in range(5):
        _ticket(client, issue_type=f"VPN Issue {index}")

    body = client.get("/tickets/", params={"page": 1, "page_size": 2}).json()
    assert body["total"] == 5
    assert len(body["items"]) == 2

    body = client.get("/tickets/", params={"page": 3, "page_size": 2}).json()
    assert len(body["items"]) == 1


def test_list_rejects_invalid_status(client, seed):
    assert client.get("/tickets/", params={"status": "Bogus"}).status_code == 422


def test_list_rejects_invalid_sort_field(client, seed):
    assert client.get("/tickets/", params={"sort_by": "drop table"}).status_code == 422


def test_list_rejects_invalid_date(client, seed):
    response = client.get("/tickets/", params={"opened_from": "31-31-2026"})
    assert response.status_code == 422


def test_filter_by_priority(client, seed):
    _ticket(client, priority="High", issue_type="Outage")
    _ticket(client, priority="Low", issue_type="Typo")

    body = client.get("/tickets/", params={"priority": "Low"}).json()
    assert body["total"] == 1
    assert body["items"][0]["issue_type"] == "Typo"


def test_filter_by_sla_state_breached(client, db, seed):
    ticket = models.Ticket(
        issue_type="Old outage",
        category_id=1,
        sla_policy_id=seed["policies"]["High"].id,
        status="New",
        date_opened=datetime.utcnow() - timedelta(hours=100),
    )
    db.add(ticket)
    db.commit()

    body = client.get("/tickets/", params={"sla_state": "breached"}).json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == ticket.id

    body = client.get("/tickets/", params={"sla_state": "on_track"}).json()
    assert body["total"] == 0


def test_sla_state_sql_matches_in_memory_evaluation(client, db, seed):
    """Garante paridade entre o filtro SQL e evaluate_ticket()."""
    for hours_ago in (1, 20, 30):
        db.add(
            models.Ticket(
                issue_type=f"Ticket {hours_ago}h",
                category_id=1,
                sla_policy_id=seed["policies"]["High"].id,
                status="In Progress",
                date_opened=datetime.utcnow() - timedelta(hours=hours_ago),
            )
        )
    db.add(
        models.Ticket(
            issue_type="Resolved fast",
            category_id=1,
            sla_policy_id=seed["policies"]["High"].id,
            status="Closed",
            date_opened=datetime.utcnow() - timedelta(hours=30),
            date_resolved=datetime.utcnow() - timedelta(hours=20),
            resolution_time_hours=10,
        )
    )
    db.commit()

    rows = client.get("/tickets/", params={"page_size": 50}).json()["items"]
    memory = {row["id"]: row["sla_state"] for row in rows}

    for state in ("on_track", "at_risk", "breached", "met"):
        filtered = client.get(
            "/tickets/", params={"sla_state": state, "page_size": 50}
        ).json()
        from_sql = {item["id"] for item in filtered["items"]}
        from_memory = {tid for tid, value in memory.items() if value == state}
        assert from_sql == from_memory, state