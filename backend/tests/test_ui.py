def test_dashboard_route_serves_html(client, seed):
    response = client.get("/ui")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "SupportOps" in response.text


def test_static_assets_are_served(client, seed):
    css = client.get("/static/styles.css")
    js = client.get("/static/app.js")
    assert css.status_code == 200
    assert js.status_code == 200
    assert "--accent" in css.text
    assert "SLA_LABEL" in js.text


def test_root_advertises_dashboard(client, seed):
    body = client.get("/").json()
    assert body["dashboard"] == "/ui"
