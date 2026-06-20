"""Aggregate metric time series for charts (REST)."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.api.deps import get_scenario_manager, require_scenario
from app.models.schemas import MetricSeries, Mode
from app.services.scenario_manager import ScenarioManager

router = APIRouter(prefix="/scenarios/{scenario_id}", tags=["metrics"])


@router.get("/metrics", response_model=MetricSeries)
def metric_series(
    scenario_id: str,
    from_tick: int = Query(0, ge=0),
    to_tick: int = Query(10**9, ge=0),
    manager: ScenarioManager = Depends(get_scenario_manager),
) -> MetricSeries:
    """Per-tick aggregates within ``[from_tick, to_tick]`` from the in-process buffer."""
    require_scenario(manager, scenario_id)
    state = manager._state.get(scenario_id)  # noqa: SLF001 - internal store access by owner
    points = state.metric_window(from_tick, to_tick) if state else []
    return MetricSeries(
        scenario_id=scenario_id,
        from_tick=from_tick,
        to_tick=to_tick,
        points=points,
    )


@router.get("/export")
def export_metrics(
    scenario_id: str,
    format: str = Query("csv", pattern="^(csv|json)$"),
    from_tick: int = Query(0, ge=0),
    to_tick: int = Query(10**9, ge=0),
    manager: ScenarioManager = Depends(get_scenario_manager),
) -> Response:
    """Export the per-tick aggregate metrics as a downloadable file.

    CSV is the spec default for inter-team handoff (sim and data teams can
    open it in pandas or Excel). JSON is useful for quick UI downloads.
    Parquet/larger formats live in the data subsystem, not here.
    """
    require_scenario(manager, scenario_id)
    state = manager._state.get(scenario_id)  # noqa: SLF001
    points = state.metric_window(from_tick, to_tick) if state else []

    if not points:
        raise HTTPException(
            status_code=404,
            detail="No metrics buffered for this scenario yet — start the run first.",
        )

    filename = f"{scenario_id}_metrics_{from_tick}-{points[-1].tick}.{format}"
    if format == "json":
        body = MetricSeries(
            scenario_id=scenario_id, from_tick=from_tick, to_tick=to_tick, points=points
        ).model_dump_json()
        return Response(
            content=body,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    buf = io.StringIO()
    writer = csv.writer(buf)
    mode_cols = [m.value for m in Mode]
    writer.writerow(
        [
            "tick",
            "sim_time_minutes",
            "rain_intensity",
            "avg_commute_minutes",
            "metro_load_pct",
            "bus_load_pct",
            "road_congestion_index",
            "aqi_estimate",
            "agents_commuting",
            *[f"mode_share_{m}" for m in mode_cols],
        ]
    )
    for p in points:
        writer.writerow(
            [
                p.tick,
                p.sim_time_minutes,
                p.rain_intensity,
                p.avg_commute_minutes,
                p.metro_load_pct,
                p.bus_load_pct,
                p.road_congestion_index,
                p.aqi_estimate,
                p.agents_commuting,
                *[p.mode_share.get(Mode(m), 0.0) for m in mode_cols],
            ]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
