"""Misiones: frente de Pareto del genético y selección por pesos (features 004 y 005)."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request

from marsmap.api.deps import ApiError, RegionDep, limit_compute, limit_mission
from marsmap.api.schemas import (
    DiscardOut,
    LegOut,
    LineString,
    MissionOut,
    MissionRequest,
    MissionResultOut,
    SelectRequest,
)
from marsmap.planning.mission.config import load_config
from marsmap.planning.mission.poi import pois_to_geojson
from marsmap.planning.mission.select import select_mission
from marsmap.planning.mission.service import MissionPlan, plan_missions
from marsmap.planning.service import RouteError

router = APIRouter()
_CFG = load_config()

LIMITATIONS = [
    "Modelo de energía y velocidad genérico de demo (no es el de Perseverance).",
    "El valor científico de cada punto está asignado a mano, no calculado desde datos CRISM.",
    "La transitabilidad se calcula solo por pendiente: no ve arena blanda ni rocas individuales.",
]


@router.get("/regions/{region_id}/pois")
def pois(region: RegionDep) -> dict:
    return pois_to_geojson(region.pois)


def _mission_out(plan: MissionPlan, mission) -> MissionOut:
    ids = [plan.pois[k - 1].poi_id for k in mission.sequence]
    m = mission.metrics
    return MissionOut(
        mission_id=mission.mission_id,
        sequence=ids,
        geometry=LineString(coordinates=plan.geometry(mission)),
        legs=[LegOut.model_validate(leg) for leg in plan.legs(mission)],
        science_total=m.science_total,
        time_h=m.time_h,
        energy_wh=m.energy_wh,
        risk_m=m.risk_m,
        risk_score=m.risk_score,
        distance_m=m.distance_m,
        max_slope_deg=m.max_slope_deg,
        explanations=plan.explanations[mission.mission_id],
    )


@router.post(
    "/regions/{region_id}/missions",
    response_model=MissionResultOut,
    dependencies=[Depends(limit_mission)],
)
def create_missions(region: RegionDep, body: MissionRequest, request: Request) -> MissionResultOut:
    candidates = region.pois
    if body.poi_ids is not None:
        known = {p.poi_id: p for p in region.pois}
        unknown = [i for i in body.poi_ids if i not in known]
        if unknown:
            raise ApiError(422, "unknown_poi", f"POI desconocido(s): {', '.join(unknown[:3])}")
        candidates = [known[i] for i in dict.fromkeys(body.poi_ids)]
    params = body.model_dump(mode="json")
    params["poi_ids"] = [p.poi_id for p in candidates]
    result_id = hashlib.sha256(
        json.dumps([region.region.region_id, params], sort_keys=True).encode()
    ).hexdigest()[:16]
    plans = request.app.state.plans
    plan = plans.get(result_id)
    if plan is None:
        try:
            plan = plan_missions(
                region.grid, (body.habitat.lat, body.habitat.lon), candidates,
                region.zones if body.use_forbidden_zones else [], _CFG,
                body.energy_budget_wh, body.max_time_h, body.max_radius_m,
                body.seed, body.pop_size, body.n_generations,
            )  # fmt: skip
        except RouteError as exc:
            raise ApiError(422, exc.code, exc.message) from exc
        plans.put(result_id, plan)
    return MissionResultOut(
        result_id=result_id,
        front=[_mission_out(plan, m) for m in plan.front],
        named=plan.named,
        discarded=[
            DiscardOut(poi_id=d.poi_id, reason_code=d.reason_code, reason=d.reason)
            for d in plan.discarded
        ],
        params_used={
            **params,
            "energy_budget_wh": plan.energy_budget_wh,
            "max_time_h": plan.max_time_h,
            "max_radius_m": plan.max_radius_m,
        },
        limitations=LIMITATIONS,
        compute_ms=plan.compute_ms,
    )


@router.post(
    "/regions/{region_id}/missions/{result_id}/select",
    response_model=MissionOut,
    dependencies=[Depends(limit_compute)],
)
def select(
    region: RegionDep,
    result_id: Annotated[str, Path(pattern=r"^[0-9a-f]{16}$")],
    body: SelectRequest,
    request: Request,
) -> MissionOut:
    plan = request.app.state.plans.get(result_id)
    if plan is None:
        raise ApiError(
            404, "result_expired", "El resultado ya no está disponible; vuelve a planificar."
        )
    mission = select_mission(plan.front, body.model_dump())
    return _mission_out(plan, mission)
