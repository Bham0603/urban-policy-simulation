# Calibration Documentation — Delhi Urban Simulation

> Phase 2 baseline calibration (PRD §4, SUB-01, task 1.4)

## Overview

This document records the expected output ranges for the default `scenario_a` configuration and the published data sources used to calibrate them. The simulation aims to reproduce realistic Delhi commuting dynamics within ±20% of published statistics (PRD metric M2).

## Published Data Sources

| Source | Data | Year | Used For |
|--------|------|------|----------|
| RITES Comprehensive Mobility Plan | Mode share survey | 2018 | Mode share targets |
| DMRC Annual Report | Daily ridership per station | 2023 | Metro load calibration |
| RITES CMP | Average commute time study | 2018 | Avg commute target (34 min) |
| CPCB Delhi | Emission inventory | 2022 | AQI estimation factors |
| TERI | Modal emission study | 2021 | PM2.5 per passenger-km |
| DMRC Public Timetable | Peak/off-peak headways | 2024 | DMRC frequency schedule |

## Calibration Targets

### Mode Share (RITES 2018)

| Mode | Target Share | Tolerance |
|------|-------------|-----------|
| Metro | 15.5% | ±5% |
| Bus | 18.0% | ±5% |
| Two-Wheeler (Bike) | 12.0% | ±5% |
| Car | 12.0% | ±5% |
| Walk | 14.0% | ±5% |
| Auto-rickshaw | 12.0% | ±5% |
| Bike Share | 3.0% | ±3% |
| E-Rickshaw | 6.5% | ±5% |

### Baseline Metric Ranges (PRD §4, task 1.1)

These are the acceptance criteria for a `scenario_a` run with default parameters:

| Metric | Acceptable Range | Notes |
|--------|-----------------|-------|
| `avg_commute_minutes` | [25, 42] | Within ±20% of RITES 34 min |
| `metro_load_pct` (peak) | [25, 70] | At peak commuting period |
| `road_congestion_index` | [0.2, 0.8] | During peak hours |

### DMRC Ridership (2023)

| Station | Daily Footfall |
|---------|---------------|
| Rajiv Chowk | 500,000 |
| New Delhi | 400,000 |
| Patel Chowk | 80,000 |
| Barakhamba Road | 120,000 |
| RK Ashram Marg | 100,000 |

## Calibration Parameters

### Default `scenario_a` Configuration

```json
{
  "name": "scenario_a",
  "population": 5000,
  "seed": 42,
  "tick_minutes": 5,
  "params": {
    "bus_capacity_pct": 1.0,
    "fuel_price_delta_paise": 0
  }
}
```

### Key Tuning Knobs

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Metro capacity denominator | `pop × 0.08` | Tuned so 15% metro ridership → [25,70]% load |
| Bus capacity denominator | `pop × 0.06` | Tuned for realistic bus load percentages |
| BPR alpha (mixed-traffic) | 0.20 | Slightly above standard BPR (0.15) for Indian mixed-traffic |
| BPR beta | 4.0 | Standard exponential growth |
| Congestion cap | 9.0× | Prevents infinite delay spikes |
| Rain speed reduction | up to 40% | On car free-flow speed |
| Rain capacity reduction | up to 30% | On road lane capacity |

### Mode Choice Model (MNL)

The mode choice model uses per-occupation utility weights:

| Occupation | β_time | β_cost | β_comfort | β_weather | β_habit |
|-----------|--------|--------|-----------|-----------|---------|
| Office Executive | -0.15 | -0.012 | 1.8 | -0.4 | 0.4 |
| Student | -0.04 | -0.06 | 0.1 | -1.5 | 0.3 |
| Blue-collar Worker | -0.10 | -0.04 | 0.2 | -1.2 | 0.5 |
| Gig Worker | -0.18 | -0.05 | 0.1 | -1.0 | 0.2 |
| Retired Citizen | -0.03 | -0.025 | 1.2 | -2.5 | 0.6 |

### DMRC Frequency Schedule

| Line | Peak Headway | Off-Peak Headway | Trains/Dir | Capacity/Train |
|------|-------------|-----------------|------------|----------------|
| Yellow | 2:15 (135s) | 5:00 (300s) | 8 | 1,800 |
| Blue | 2:30 (150s) | 4:30 (270s) | 10 | 1,800 |
| Red | 3:00 (180s) | 6:00 (360s) | 6 | 1,600 |
| Green | 3:30 (210s) | 7:00 (420s) | 4 | 1,400 |
| Violet | 2:45 (165s) | 5:30 (330s) | 7 | 1,800 |

Peak windows: 7:00–10:30 AM and 5:00–8:30 PM.

## Verification

Run the calibration test suite:

```bash
cd simulation
python -m pytest tests/test_baseline_calibration.py -v
python -m pytest tests/test_calibration.py -v
```

## Revision History

| Date | Change | Author |
|------|--------|--------|
| 2026-06-25 | Initial Phase 2 calibration document | purav |
