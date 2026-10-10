"""Planificación de rutas A* (feature 003)."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request

from marsmap.api.deps import ApiError, RegionDep, limit_compute
from marsmap.api.schemas import LineString, PresetOut, ProfilePoint, RouteOut, RouteRequest
from marsmap.planning.astar import SearchTimeout
from marsmap.planning.presets import PRESET_LABELS, PRESETS
from marsmap.planning.service import RouteError, build_constrained_costmap, plan_route

router = APIRouter()


@router.get("/regions/{region_id}/route/presets", response_model=list[PresetOut])
def presets(region: RegionDep) -> list[PresetOut]:
    return [PresetOut(preset=k, label=PRESET_LABELS[k], weights=w) for k, w in PRESETS.items()]


@router.post(
    "/regions/{region_id}/route", response_model=RouteOut, dependencies=[Depends(limit_compute)]
)
def route(region: RegionDep, body: RouteRequest, request: Request) -> RouteOut:
    t0 = time.perf_counter()
    weights = (
        body.weights
        if body.preset is None and body.weights is not None
        else PRESETS[body.preset or "balanced"]
    )
    zones = region.zones if body.use_forbidden_zones else []
    habitat = (body.habitat.lat, body.habitat.lon) if body.habitat else None
    grid = region.grid
    key = (
        region.region.region_id,
        tuple(weights.model_dump().values()),
        habitat,
        body.max_radius_m,
        body.use_forbidden_zones,
    )
    costmaps = request.app.state.costmaps
    cm = costmaps.get(key)
    if cm is None:
        pois = [p.model_dump() for p in region.pois] if weights.science > 0 else None
        cm = build_constrained_costmap(grid, weights, zones, habitat, body.max_radius_m, pois)
        costmaps.put(key, cm)
    try:
        res = plan_route(
            grid, (body.start.lat, body.start.lon), (body.goal.lat, body.goal.lon), weights, zones,
            costmap=cm, timeout_s=request.app.state.settings.compute_timeout_s,
        )  # fmt: skip
    except RouteError as exc:
        raise ApiError(422, exc.code, exc.message) from exc
    except SearchTimeout as exc:
        raise ApiError(504, "timeout", "El cálculo superó el tiempo máximo permitido.") from exc
    ms = int((time.perf_counter() - t0) * 1000)
    if res.status != "ok":
        return RouteOut(status="no_route", reason=res.reason, weights_used=weights, compute_ms=ms)
    m = res.metrics
    coords = [list(grid.to_lonlat(r, c)) for r, c in res.cells]
    return RouteOut(
        status="ok",
        geometry=LineString(coordinates=coords),
        distance_m=m.distance_m,
        straight_line_m=m.straight_line_m,
        tortuosity=m.tortuosity,
        max_slope_deg=m.max_slope_deg,
        mean_slope_deg=m.mean_slope_deg,
        elevation_gain_m=m.elevation_gain_m,
        elevation_loss_m=m.elevation_loss_m,
        pct_risk_cells=m.pct_risk_cells,
        est_time_h=m.est_time_h,
        profile=[ProfilePoint(**p) for p in m.profile],
        explanations=res.explanations,
        weights_used=weights,
        compute_ms=ms,
    )
