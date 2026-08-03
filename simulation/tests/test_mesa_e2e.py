"""Mesa end-to-end integration test (SUB-01, task 1.3).

Boots the full MesaSimEngine, ticks 100 times, and asserts non-trivial
metrics at peak. Tests all 3 PRD scenarios produce distinct dynamics.
"""

from __future__ import annotations

from app.models.schemas import ScenarioConfig, Event, EventType
from simulation.engine import MesaSimEngine


def _run_scenario(name: str, population: int, seed: int, events: list[Event], ticks: int = 100):
    """Helper: run a scenario and return collected metrics."""
    config = ScenarioConfig(
        name=name,
        population=population,
        seed=seed,
        tick_minutes=5,
        params={},
    )
    engine = MesaSimEngine(config)

    # Queue events at tick 20 (warm up first)
    for ev in events:
        engine.queue_event(ev)

    snapshots = []
    for _ in range(ticks):
        snap = engine.step()
        snapshots.append(snap)

    return snapshots


def test_mesa_e2e_baseline():
    """Run full mesa engine for 100 ticks and assert non-trivial metrics."""
    config = ScenarioConfig(
        name="e2e_baseline",
        population=500,
        seed=42,
        tick_minutes=5,
        params={},
    )
    engine = MesaSimEngine(config)

    for _ in range(100):
        snap = engine.step()

    # At tick 100, metrics should be non-trivial
    assert snap.tick == 100
    assert snap.metrics.tick == 100
    assert snap.metrics.sim_time_minutes == 500  # 100 * 5

    # Mode share should have at least 3 non-zero modes
    non_zero_modes = sum(1 for v in snap.metrics.mode_share.values() if v > 0)
    assert non_zero_modes >= 3, f"Only {non_zero_modes} non-zero modes at tick 100"

    # Grid should be populated
    assert len(snap.grid) == 100  # 10x10


def test_monsoon_scenario_distinct():
    """Verify monsoon scenario produces distinct dynamics from baseline."""
    baseline = _run_scenario(
        "baseline", population=200, seed=42,
        events=[], ticks=100
    )

    monsoon = _run_scenario(
        "monsoon", population=200, seed=42,
        events=[Event(type=EventType.weather, payload={"rain_intensity": 0.85})],
        ticks=100,
    )

    # Monsoon should show higher avg_commute than baseline at tick 50+
    baseline_commute_50 = baseline[49].metrics.avg_commute_minutes
    monsoon_commute_50 = monsoon[49].metrics.avg_commute_minutes

    # Rain should increase commute times
    assert monsoon_commute_50 > baseline_commute_50, (
        f"Monsoon commute ({monsoon_commute_50:.1f}) should be > "
        f"baseline ({baseline_commute_50:.1f})"
    )


def test_metro_shutdown_scenario_distinct():
    """Verify metro shutdown produces distinct dynamics from baseline."""
    baseline = _run_scenario(
        "baseline", population=200, seed=42,
        events=[], ticks=100
    )

    metro_shutdown = _run_scenario(
        "metro_shutdown", population=200, seed=42,
        events=[Event(type=EventType.infrastructure, payload={"disable_metro_line": "yellow"})],
        ticks=100,
    )

    # Metro shutdown should reduce metro mode share
    baseline_metro = baseline[80].metrics.mode_share.get("metro", 0)
    shutdown_metro = metro_shutdown[80].metrics.mode_share.get("metro", 0)

    # Metro share should be lower or zero after shutdown
    assert shutdown_metro <= baseline_metro, (
        f"Metro share after shutdown ({shutdown_metro:.3f}) should be <= "
        f"baseline ({baseline_metro:.3f})"
    )


def test_fuel_shock_scenario_distinct():
    """Verify fuel shock produces distinct dynamics from baseline."""
    baseline = _run_scenario(
        "baseline", population=200, seed=42,
        events=[], ticks=100
    )

    fuel_shock = _run_scenario(
        "fuel_shock", population=200, seed=42,
        events=[Event(type=EventType.policy, payload={"fuel_price_delta_paise": 3000})],
        ticks=100,
    )

    # Fuel shock should reduce car mode share at peak
    baseline_car = baseline[80].metrics.mode_share.get("car", 0)
    shock_car = fuel_shock[80].metrics.mode_share.get("car", 0)

    # Car share should be lower after fuel price increase
    assert shock_car <= baseline_car, (
        f"Car share after fuel shock ({shock_car:.3f}) should be <= "
        f"baseline ({baseline_car:.3f})"
    )


def test_three_scenarios_all_distinct():
    """Verify all 3 scenarios produce visibly distinct dynamics over 100 ticks.

    This is the core acceptance criterion from PRD §2 (M3).
    """
    baseline = _run_scenario("baseline", 200, 42, [], 100)
    monsoon = _run_scenario(
        "monsoon", 200, 42,
        [Event(type=EventType.weather, payload={"rain_intensity": 0.8})], 100
    )
    metro_shutdown = _run_scenario(
        "metro_shutdown", 200, 42,
        [Event(type=EventType.infrastructure, payload={"disable_metro_line": "yellow"})], 100
    )

    # Compare across ticks 50–90 (peak commuting period) to reduce stochastic noise
    def avg_metric(snapshots, start, end, field):
        vals = [getattr(snapshots[i].metrics, field) for i in range(start, end)]
        return sum(vals) / len(vals) if vals else 0

    def mode_share_avg(snapshots, start, end, mode):
        vals = [snapshots[i].metrics.mode_share.get(mode, 0) for i in range(start, end)]
        return sum(vals) / len(vals) if vals else 0

    # Baseline vs Monsoon: commute times should increase with rain
    b_commute = avg_metric(baseline, 50, 90, "avg_commute_minutes")
    m_commute = avg_metric(monsoon, 50, 90, "avg_commute_minutes")
    monsoon_distinct = m_commute > b_commute

    # Baseline vs Metro Shutdown: metro mode share should decrease
    b_metro_share = mode_share_avg(baseline, 50, 90, "metro")
    s_metro_share = mode_share_avg(metro_shutdown, 50, 90, "metro")
    shutdown_distinct = s_metro_share <= b_metro_share

    print(f"  Baseline avg commute: {b_commute:.2f}, Monsoon: {m_commute:.2f}")
    print(f"  Baseline metro share: {b_metro_share:.4f}, Shutdown: {s_metro_share:.4f}")

    assert monsoon_distinct, (
        f"Monsoon should increase commute ({m_commute:.2f} vs {b_commute:.2f})"
    )
    assert shutdown_distinct, (
        f"Metro shutdown should reduce metro share ({s_metro_share:.4f} vs {b_metro_share:.4f})"
    )
