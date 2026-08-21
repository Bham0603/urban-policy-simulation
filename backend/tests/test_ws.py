"""End-to-end smoke test of the live stream — the shape of the daily integration check (ROLE_5).

Tests run against the fake engine by default. A parametrized variant exercises both fake and mesa
engines so the same assertions guard the real engine once SUB-01 lands.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.conftest import make_scenario

# Ensure simulation package is importable (same path tweak as conftest)
sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent / "simulation"))


def _mesa_available() -> bool:
    """Return True if the real Mesa-backed engine can be imported."""
    try:
        from simulation.engine import MesaSimEngine  # noqa: F401

        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Existing smoke tests (always run against the default fake engine)
# ---------------------------------------------------------------------------


def test_ws_streams_ticks(client):
    sid = make_scenario(client)["id"]
    client.post(f"/api/v1/scenarios/{sid}/start")

    with client.websocket_connect(f"/ws/scenarios/{sid}") as ws:
        first = ws.receive_json()
        assert first["type"] == "status"
        assert first["scenario_id"] == sid

        # Then tick frames should flow (fast tick interval set in conftest).
        msg = ws.receive_json()
        assert msg["type"] == "tick"
        assert msg["diff"]["scenario_id"] == sid
        assert "avg_commute_minutes" in msg["diff"]["metrics"]


def test_ws_unknown_scenario_closes(client):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/scenarios/scenario_9999") as ws:
            ws.receive_json()


# ---------------------------------------------------------------------------
# Parametrized dual-engine smoke test
# ---------------------------------------------------------------------------


@pytest.fixture(
    params=[
        "fake",
        pytest.param(
            "mesa",
            marks=pytest.mark.skipif(
                not _mesa_available(),
                reason="simulation.engine not importable — SUB-01 not installed",
            ),
        ),
    ]
)
def client_for_engine(request, tmp_path) -> Iterator[TestClient]:
    """Yield a TestClient configured to use the parametrized sim engine."""
    engine = request.param
    os.environ["BACKEND_METADATA_DB_PATH"] = str(tmp_path / "meta.sqlite")
    os.environ["BACKEND_TICK_INTERVAL_SECONDS"] = "0.01"
    os.environ["BACKEND_SIM_ENGINE"] = engine
    os.environ["BACKEND_ENVIRONMENT"] = "test"

    from app.config import get_settings

    get_settings.cache_clear()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_dual_engine_create_start_stream(client_for_engine):
    """Create → start → stream ticks → inject event → verify next tick."""
    c = client_for_engine

    # 1. Create scenario
    resp = c.post(
        "/api/v1/scenarios",
        json={"config": {"name": "dual_test", "city": "delhi", "population": 500, "seed": 99}},
    )
    assert resp.status_code == 201
    sid = resp.json()["id"]

    # 2. Start it
    resp = c.post(f"/api/v1/scenarios/{sid}/start")
    assert resp.status_code == 200

    # 3. Connect WS and receive the initial status + at least one tick
    with c.websocket_connect(f"/ws/scenarios/{sid}") as ws:
        status_msg = ws.receive_json()
        assert status_msg["type"] == "status"

        tick_msg = ws.receive_json()
        assert tick_msg["type"] == "tick"
        assert tick_msg["diff"]["tick"] >= 1
        assert "avg_commute_minutes" in tick_msg["diff"]["metrics"]

    # 4. Inject a weather event
    resp = c.post(
        f"/api/v1/scenarios/{sid}/events",
        json={"type": "WEATHER_EVENT", "payload": {"rain_intensity": 0.8, "duration_ticks": 10}},
    )
    assert resp.status_code == 200
    ack = resp.json()
    assert ack["accepted"] is True

    # 5. Stream again — the next tick should reflect the running sim
    with c.websocket_connect(f"/ws/scenarios/{sid}") as ws:
        ws.receive_json()  # status
        post_event_tick = ws.receive_json()
        assert post_event_tick["type"] == "tick"
        assert post_event_tick["diff"]["metrics"]["tick"] >= 1
