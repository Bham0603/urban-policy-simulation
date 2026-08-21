def test_root_returns_service_info(client):
    """The bare host shouldn't 404 — landing should hint at /docs etc."""
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"].startswith("Urban Intelligence Platform")
    assert "version" in body
    # The links map is the actual contract — operators rely on these names.
    assert set(body["links"]) >= {"docs", "healthz", "scenarios"}


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_readyz(client):
    resp = client.get("/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["scenarios"] == 0
