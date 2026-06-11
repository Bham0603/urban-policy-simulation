from tests.conftest import make_scenario


def test_create_and_get_scenario(client):
    created = make_scenario(client)
    assert created["id"] == "scenario_0001"
    assert created["status"] == "created"
    assert created["config"]["seed"] == 7

    got = client.get(f"/api/v1/scenarios/{created['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == created["id"]


def test_list_scenarios(client):
    make_scenario(client, "scenario_a")
    make_scenario(client, "scenario_b")
    resp = client.get("/api/v1/scenarios")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_missing_scenario_is_404(client):
    assert client.get("/api/v1/scenarios/scenario_9999").status_code == 404


def test_lifecycle_pause_and_reset(client):
    sid = make_scenario(client)["id"]

    started = client.post(f"/api/v1/scenarios/{sid}/start")
    assert started.status_code == 200
    assert started.json()["status"] == "running"

    paused = client.post(f"/api/v1/scenarios/{sid}/pause")
    assert paused.json()["status"] == "paused"

    reset = client.post(f"/api/v1/scenarios/{sid}/reset")
    assert reset.json()["status"] == "created"
    assert reset.json()["current_tick"] == 0


def test_branch_creates_new_scenario(client):
    parent = make_scenario(client)
    resp = client.post(
        f"/api/v1/scenarios/{parent['id']}/branch", json={"name": "scenario_a_branch"}
    )
    assert resp.status_code == 201
    assert resp.json()["id"] != parent["id"]
    assert resp.json()["config"]["name"] == "scenario_a_branch"


def test_delete_scenario(client):
    sid = make_scenario(client)["id"]
    assert client.delete(f"/api/v1/scenarios/{sid}").status_code == 204
    assert client.get(f"/api/v1/scenarios/{sid}").status_code == 404


def test_snapshot_and_event_injection(client):
    sid = make_scenario(client)["id"]

    snap = client.get(f"/api/v1/scenarios/{sid}/snapshot")
    assert snap.status_code == 200
    assert snap.json()["tick"] == 0

    ack = client.post(
        f"/api/v1/scenarios/{sid}/events",
        json={"type": "WEATHER_EVENT", "payload": {"rain_intensity": 0.9, "duration_ticks": 30}},
    )
    assert ack.status_code == 200
    assert ack.json()["accepted"] is True
    assert ack.json()["queued_for_tick"] == 1


def test_export_404_when_empty(client):
    """Calling export before any tick has run should 404, not return an empty file."""
    sid = make_scenario(client)["id"]
    resp = client.get(f"/api/v1/scenarios/{sid}/export?format=csv")
    assert resp.status_code == 404


def test_export_csv_after_ticks(client):
    """Export returns a CSV with one row per buffered tick once the run has ticked."""
    import time

    sid = make_scenario(client)["id"]
    client.post(f"/api/v1/scenarios/{sid}/start")
    # Settings.tick_interval_seconds = 0.01 in tests; wait a few ticks.
    time.sleep(0.1)
    client.post(f"/api/v1/scenarios/{sid}/pause")

    resp = client.get(f"/api/v1/scenarios/{sid}/export?format=csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    lines = resp.text.strip().splitlines()
    assert len(lines) >= 2  # header + at least one row
    assert lines[0].startswith("tick,sim_time_minutes,rain_intensity")
    assert "mode_share_metro" in lines[0]


def test_export_json_round_trip(client):
    import time

    sid = make_scenario(client)["id"]
    client.post(f"/api/v1/scenarios/{sid}/start")
    time.sleep(0.1)
    client.post(f"/api/v1/scenarios/{sid}/pause")

    resp = client.get(f"/api/v1/scenarios/{sid}/export?format=json")
    assert resp.status_code == 200
    body = resp.json()
    assert body["scenario_id"] == sid
    assert len(body["points"]) >= 1
    assert body["points"][0]["tick"] >= 1
