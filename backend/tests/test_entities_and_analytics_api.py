from datetime import datetime, timedelta

from backend.app import models


def _create_closed_ticket(db, seed, priority, resolution_hours, days_ago=0):
    opened = datetime(2026, 9, 1, 9, 0, 0) - timedelta(days=days_ago)
    ticket = models.Ticket(
        issue_type=f"Issue {priority}",
        category_id=seed["categories"][0].id,
        agent_id=seed["agents"][0].id,
        sla_policy_id=seed["policies"][priority].id,
        status="Closed",
        date_opened=opened,
        date_resolved=opened + timedelta(hours=resolution_hours),
        resolution_time_hours=resolution_hours,
    )
    db.add(ticket)
    return ticket


def test_entities_listing(client, seed):
    assert len(client.get("/categories").json()) == 2
    assert len(client.get("/agents").json()) == 2
    assert len(client.get("/customers").json()) == 1


def test_sla_policies_listing(client, seed):
    policies = client.get("/sla-policies").json()
    assert [p["priority"] for p in policies] == ["High", "Medium", "Low"]


def test_entity_counts(client, db, seed):
    _create_closed_ticket(db, seed, "High", 10)
    db.commit()

    counts = client.get("/entities/counts").json()
    assert counts["tickets"] == 1
    assert counts["categories"] == 2
    assert counts["sla_policies"] == 3


def test_agent_workload(client, db, seed):
    _create_closed_ticket(db, seed, "High", 10)
    _create_closed_ticket(db, seed, "High", 60)
    db.commit()

    body = client.get(f"/agents/{seed['agents'][0].id}/workload").json()
    assert body["tickets_handled"] == 2
    assert body["avg_resolution_time_hours"] == 35.0
    assert body["breached_tickets"] == 1


def test_analytics_overview_empty(client, seed):
    body = client.get("/analytics/overview").json()
    assert body["total_volume"] == 0
    assert body["compliance_rate_percent"] == 0.0


def test_analytics_overview_counts(client, db, seed):
    _create_closed_ticket(db, seed, "High", 10)   # met
    _create_closed_ticket(db, seed, "High", 40)   # breached
    _create_closed_ticket(db, seed, "Low", 10)    # met
    db.commit()

    body = client.get("/analytics/overview").json()
    assert body["total_volume"] == 3
    assert body["resolved_volume"] == 3
    assert body["met_sla_tickets"] == 2
    assert body["breached_tickets"] == 1
    assert body["compliance_rate_percent"] == 66.67
    assert body["median_resolution_time_hrs"] == 10.0


def test_analytics_by_priority(client, db, seed):
    _create_closed_ticket(db, seed, "High", 10)
    _create_closed_ticket(db, seed, "Low", 10)
    db.commit()

    rows = client.get("/analytics/by-priority").json()
    by_priority = {row["priority"]: row for row in rows}
    assert by_priority["High"]["tickets"] == 1
    assert by_priority["High"]["sla_limit_hours"] == 24.0


def test_analytics_sla_compliance_per_priority(client, db, seed):
    _create_closed_ticket(db, seed, "High", 10)
    _create_closed_ticket(db, seed, "High", 50)
    db.commit()

    rows = client.get("/analytics/sla-compliance").json()
    high = next(row for row in rows if row["priority"] == "High")
    assert high["resolved"] == 2
    assert high["met"] == 1
    assert high["breached"] == 1
    assert high["compliance_rate_percent"] == 50.0


def test_analytics_backlog(client, db, seed):
    db.add(
        models.Ticket(
            issue_type="Long running",
            category_id=seed["categories"][0].id,
            sla_policy_id=seed["policies"]["High"].id,
            status="In Progress",
            date_opened=datetime.utcnow() - timedelta(hours=50),
        )
    )
    db.commit()

    body = client.get("/analytics/backlog").json()
    assert body["open_count"] == 1
    assert body["breached"] == 1
    assert body["tickets"][0]["remaining_hours"] < 0


def test_analytics_by_category_and_agent(client, db, seed):
    _create_closed_ticket(db, seed, "High", 10)
    db.commit()

    assert client.get("/analytics/by-category").json()[0]["tickets"] == 1
    assert client.get("/analytics/by-agent").json()[0]["agent"] == "John"


def test_analytics_trend(client, db, seed):
    _create_closed_ticket(db, seed, "High", 10)
    db.commit()

    rows = client.get("/analytics/trend").json()
    assert rows[0]["opened"] == 1
    assert rows[0]["resolved"] == 1


def test_health_reports_database(client, seed):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["database"] == "up"