"""Calibration targets and validation utilities for Delhi simulation.

Provides published reference data from RITES 2018 mode share survey,
DMRC 2023 ridership counts, and RITES 2018 commute time study.
Used by tests and future automated calibration loops.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Delhi 2018 mode share targets (RITES survey)
# Mapped to simulation Mode enum values.
# Source: data/validation_data/mode_share_delhi.csv
# ---------------------------------------------------------------------------
DELHI_CALIBRATION_TARGETS: dict[str, float] = {
    "metro": 0.155,       # 15.5% — DMRC ridership share
    "bus": 0.180,         # 18.0% — DTC + cluster bus
    "bike": 0.120,        # 12.0% — two-wheeler (proxy from 28.5% split)
    "car": 0.120,         # 12.0% — private car
    "walk": 0.140,        # 14.0% — walk (split from Walk/Auto 26%)
    "auto": 0.120,        # 12.0% — auto-rickshaw (split from Walk/Auto 26%)
    "bike_share": 0.030,  #  3.0% — public bike-share (emerging mode)
    "e_rickshaw": 0.065,  #  6.5% — e-rickshaw (emerging mode)
}

# ---------------------------------------------------------------------------
# DMRC 2023 ridership data (daily footfall estimates)
# Source: data/validation_data/dmrc_ridership.csv
# ---------------------------------------------------------------------------
DMRC_DAILY_RIDERSHIP: dict[str, int] = {
    "Rajiv Chowk": 500_000,
    "New Delhi": 400_000,
    "Patel Chowk": 80_000,
    "Barakhamba Road": 120_000,
    "RK Ashram Marg": 100_000,
}

# ---------------------------------------------------------------------------
# Delhi average commute time target (minutes)
# Source: RITES Comprehensive Mobility Plan 2018
# ---------------------------------------------------------------------------
DELHI_AVG_COMMUTE_MIN: float = 34.0

# ---------------------------------------------------------------------------
# Validation utilities
# ---------------------------------------------------------------------------


def validate_mode_share(
    actual: dict[str, float],
    tolerance: float = 0.05,
) -> dict[str, dict]:
    """Compare simulated mode share against Delhi calibration targets.

    Parameters:
        actual: dict mapping mode name → share fraction (0..1)
        tolerance: acceptable absolute deviation (default ±5%)

    Returns:
        dict mapping mode → {"target", "actual", "delta", "pass"}
    """
    results = {}
    for mode, target in DELHI_CALIBRATION_TARGETS.items():
        actual_val = actual.get(mode, 0.0)
        delta = actual_val - target
        results[mode] = {
            "target": target,
            "actual": round(actual_val, 4),
            "delta": round(delta, 4),
            "pass": abs(delta) <= tolerance,
        }
    return results


def validate_avg_commute(
    actual: float,
    target: float = DELHI_AVG_COMMUTE_MIN,
    tolerance: float = 10.0,
) -> bool:
    """Check if average commute time is within tolerance of Delhi target.

    Parameters:
        actual: simulated average commute time in minutes
        target: Delhi reference commute time (default 34 min)
        tolerance: acceptable deviation in minutes (default ±10)

    Returns:
        True if within tolerance
    """
    return abs(actual - target) <= tolerance
