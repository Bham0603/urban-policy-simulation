from __future__ import annotations

import pytest

from app.models.schemas import Event, EventType, ScenarioConfig
from app.sim.adapter import DataPaths, SimEngine, build_engine


def _mesa_available() -> bool:
    """Return True if the real Mesa-backed engine can be imported."""
    try:
        from simulation.engine import MesaSimEngine  # noqa: F401

        return True
    except Exception:
        return False


def test_build_engine_fake():
    config = ScenarioConfig(
        name="test_fake_scenario",
        city="delhi",
        population=100,
        seed=123,
    )
    engine = build_engine("fake", config)
    assert isinstance(engine, SimEngine)
    assert engine.current_tick == 0

    # Test basic stepping
    snap = engine.step()
    assert snap.tick == 1
    assert snap.metrics.tick == 1

    # Test event queueing
    event = Event(type=EventType.weather, payload={"rain_intensity": 0.5})
    queued = engine.queue_event(event)
    assert queued == 2  # queue_event returns tick it is queued for (current_tick + 1)


def test_build_engine_fake_ignores_data_paths():
    """Fake engine works when data_paths is passed (it just ignores them)."""
    config = ScenarioConfig(name="test_dp", city="delhi", population=100, seed=1)
    from pathlib import Path

    dp = DataPaths(
        road_network=Path("a"),
        metro_network=Path("b"),
        bus_routes=Path("c"),
        population=Path("d"),
        weather=Path("e"),
    )
    engine = build_engine("fake", config, data_paths=dp)
    assert isinstance(engine, SimEngine)
    assert engine.current_tick == 0


def test_build_engine_unknown_raises():
    config = ScenarioConfig(name="test_unknown", city="delhi", population=100, seed=1)
    with pytest.raises(ValueError, match="Unknown sim engine"):
        build_engine("nonexistent", config)


@pytest.mark.skipif(
    not _mesa_available(),
    reason="simulation.engine not importable — SUB-01 not installed",
)
def test_build_engine_mesa():
    config = ScenarioConfig(
        name="test_mesa_scenario",
        city="delhi",
        population=100,
        seed=123,
    )
    engine = build_engine("mesa", config)
    assert isinstance(engine, SimEngine)
    assert engine.current_tick == 0

    # Test basic stepping
    snap = engine.step()
    assert snap.tick == 1
    assert snap.metrics.tick == 1

    # Test event queueing
    event = Event(type=EventType.weather, payload={"rain_intensity": 0.5})
    queued = engine.queue_event(event)
    assert queued == 2
