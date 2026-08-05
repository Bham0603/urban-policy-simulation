"""Tests for Phase 2 DMRC frequency schedule (SUB-03, task 3.1).

Validates schedule loading, peak/off-peak detection, and wait time calculation.
"""

from __future__ import annotations

from simulation.network import MultiModalNetwork, DMRCLineSchedule


def test_dmrc_schedule_loading():
    """Verify DMRC schedule JSON loads correctly into the network."""
    from pathlib import Path

    net = MultiModalNetwork()
    schedule_path = Path(__file__).resolve().parent.parent / "data" / "dmrc_schedule.json"

    if not schedule_path.exists():
        # Skip if data file not available
        return

    net.load_dmrc_schedule(schedule_path)

    # Should have loaded at least yellow and blue lines
    assert "yellow" in net._dmrc_schedule
    assert "blue" in net._dmrc_schedule

    yellow = net._dmrc_schedule["yellow"]
    assert yellow.peak_headway_sec == 135
    assert yellow.offpeak_headway_sec == 300
    assert yellow.capacity_per_train == 1800


def test_peak_detection():
    """Verify peak/off-peak time detection works correctly."""
    sched = DMRCLineSchedule(
        name="test",
        peak_headway_sec=120,
        offpeak_headway_sec=300,
        peak_windows=[(420, 630), (1020, 1230)],  # 7:00-10:30, 17:00-20:30
    )

    # 8:30 AM (510 min) — should be peak
    assert sched.is_peak(510) is True

    # 2:00 PM (840 min) — should be off-peak
    assert sched.is_peak(840) is False

    # 6:00 PM (1080 min) — should be peak
    assert sched.is_peak(1080) is True

    # 11:00 PM (1380 min) — should be off-peak
    assert sched.is_peak(1380) is False


def test_peak_headway_less_than_offpeak():
    """Verify peak headway is always less than off-peak headway."""
    sched = DMRCLineSchedule(
        name="test",
        peak_headway_sec=135,
        offpeak_headway_sec=300,
        peak_windows=[(420, 630), (1020, 1230)],
    )

    peak_headway = sched.get_headway_sec(510)  # 8:30 AM
    offpeak_headway = sched.get_headway_sec(840)  # 2:00 PM

    assert peak_headway < offpeak_headway


def test_wait_time_peak_vs_offpeak():
    """Verify wait times at peak < wait times at off-peak."""
    sched = DMRCLineSchedule(
        name="test",
        peak_headway_sec=135,
        offpeak_headway_sec=300,
        peak_windows=[(420, 630), (1020, 1230)],
    )

    wait_peak = sched.get_wait_time_min(510)  # 8:30 AM
    wait_offpeak = sched.get_wait_time_min(840)  # 2:00 PM

    assert wait_peak < wait_offpeak
    # Peak wait should be ~1.125 min (135/2/60)
    assert abs(wait_peak - 1.125) < 0.01
    # Off-peak wait should be ~2.5 min (300/2/60)
    assert abs(wait_offpeak - 2.5) < 0.01


def test_no_service_outside_hours():
    """Verify long wait time when outside operating hours."""
    sched = DMRCLineSchedule(
        name="test",
        peak_headway_sec=135,
        offpeak_headway_sec=300,
        peak_windows=[(420, 630)],
        first_train_min=360,  # 6:00 AM
        last_train_min=1380,  # 11:00 PM
    )

    # 4:00 AM (240 min) — no service
    wait = sched.get_wait_time_min(240)
    assert wait >= 60.0  # effectively blocked

    # 11:30 PM (1410 min) — no service
    wait = sched.get_wait_time_min(1410)
    assert wait >= 60.0


def test_capacity_during_service():
    """Verify metro capacity is non-zero during service hours."""
    sched = DMRCLineSchedule(
        name="test",
        peak_headway_sec=135,
        offpeak_headway_sec=300,
        peak_windows=[(420, 630)],
        first_train_min=360,
        last_train_min=1380,
        capacity_per_train=1800,
        trains_per_direction=8,
    )

    # During service
    cap = sched.get_capacity_this_tick(510)
    assert cap == 8 * 1800  # 14,400

    # Outside service
    cap_off = sched.get_capacity_this_tick(240)
    assert cap_off == 0


def test_metro_wait_time_network():
    """Verify network-level metro wait time works with loaded schedule."""
    from pathlib import Path

    net = MultiModalNetwork()
    schedule_path = Path(__file__).resolve().parent.parent / "data" / "dmrc_schedule.json"

    if not schedule_path.exists():
        return

    net.load_dmrc_schedule(schedule_path)

    # Yellow line at 8:30 AM (peak)
    wait_peak = net.get_metro_wait_time("yellow", 510)
    # Yellow line at 2:00 PM (off-peak)
    wait_offpeak = net.get_metro_wait_time("yellow", 840)

    assert wait_peak < wait_offpeak

    # Unknown line should return default
    wait_unknown = net.get_metro_wait_time("magenta", 510)
    assert wait_unknown == 2.5  # default fallback
