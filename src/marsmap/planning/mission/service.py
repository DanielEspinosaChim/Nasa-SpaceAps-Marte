"""Orquestación de una misión: prefiltro → matriz de tramos → NSGA-II → misiones con nombre."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from marsmap.planning.mission.config import MissionConfig
from marsmap.planning.mission.explain import explain_mission
from marsmap.planning.mission.legs import LegMatrix, build_leg_matrix
from marsmap.planning.mission.optimize import Mission, plan_front
from marsmap.planning.mission.poi import PointOfInterest
from marsmap.planning.mission.prefilter import Discard, prefilter
from marsmap.planning.mission.select import name_missions
from marsmap.planning.presets import PRESETS
from marsmap.planning.service import RouteError, build_constrained_costmap
from marsmap.planning.terrain_grid import TerrainGrid


@dataclass
class MissionPlan:
    front: list[Mission]
    named: dict[str, str]
    discarded: list[Discard]
    pois: list[PointOfInterest]  # los que entraron a la optimización (nodo k ↔ pois[k-1])
    lm: LegMatrix
    grid: TerrainGrid
    cfg: MissionConfig
    energy_budget_wh: float
    max_time_h: float
    max_radius_m: float
    explanations: dict[str, list[str]] = field(default_factory=dict)
    compute_ms: int = 0

    def mission(self, mission_id: str) -> Mission:
        return next(m for m in self.front if m.mission_id == mission_id)

    def geometry(self, mission: Mission) -> list[list[float]]:
        """LineString [lon, lat]: hábitat → POI… → hábitat."""
        coords: list[list[float]] = []
        nodes = (0, *mission.sequence, 0) if mission.sequence else ()
        for a, b in zip(nodes[:-1], nodes[1:], strict=False):
            for i, (r, c) in enumerate(self.lm.paths[(a, b)]):
                if coords and i == 0:
                    continue
                lon, lat = self.grid.to_lonlat(r, c)
                coords.append([lon, lat])
        if not coords:  # misión vacía: el rover no sale del hábitat
            lon, lat = self.grid.to_lonlat(*self.lm.node_rc[0])
            coords = [[lon, lat], [lon, lat]]
        return coords

    def legs(self, mission: Mission) -> list[dict]:
        """Tramos de la misión; una misión vacía (el rover no sale del hábitat) no tiene tramos."""
        if not mission.sequence:
            return []
        nodes = (0, *mission.sequence, 0)
        ids = ["habitat", *(p.poi_id for p in self.pois)]
        lm = self.lm
        return [
            {
                "from": ids[a],
                "to": ids[b],
                "distance_m": float(lm.distance_m[a, b]),
                "time_h": float(lm.time_h[a, b]),
                "energy_wh": float(lm.energy_wh[a, b]),
                "risk_m": float(lm.risk_m[a, b]),
                "max_slope_deg": float(lm.max_slope_deg[a, b]),
                "coordinates": [
                    [lon, lat]
                    for lon, lat in (self.grid.to_lonlat(r, c) for r, c in lm.paths[(a, b)])
                ],
            }
            for a, b in zip(nodes[:-1], nodes[1:], strict=True)
        ]


def plan_missions(
    grid: TerrainGrid,
    habitat: tuple[float, float],
    pois: list[PointOfInterest],
    zones: list[dict],
    cfg: MissionConfig,
    energy_budget_wh: float | None = None,
    max_time_h: float | None = None,
    max_radius_m: float | None = None,
    seed: int = 42,
    pop_size: int | None = None,
    n_generations: int | None = None,
) -> MissionPlan:
    """`habitat` es (lat, lon). Lanza RouteError (out_of_region / habitat_blocked)."""
    t0 = time.perf_counter()
    budget = energy_budget_wh or cfg.energy_budget_wh
    t_max = max_time_h or cfg.max_time_h
    radius = max_radius_m or cfg.max_radius_m

    kept, discarded = prefilter(pois, grid, zones, habitat, radius)
    cm = build_constrained_costmap(grid, PRESETS["balanced"], zones, habitat, radius)
    hab_rc = grid.to_rowcol(*habitat)
    if hab_rc is None:
        raise RouteError("out_of_region", "el hábitat está fuera de la región")
    if cm.blocked[hab_rc]:
        raise RouteError(
            "habitat_blocked", "el hábitat cae en terreno bloqueado o en una zona prohibida"
        )

    def reachable_pois(candidates):
        rcs = [grid.to_rowcol(p.lat, p.lon) for p in candidates]
        ok = [
            p
            for p, rc in zip(candidates, rcs, strict=True)
            if rc is not None and not cm.blocked[rc]
        ]
        for p, rc in zip(candidates, rcs, strict=True):
            if rc is None or cm.blocked[rc]:
                discarded.append(
                    Discard(
                        p.poi_id,
                        "unreachable",
                        f"{p.name} cae en terreno bloqueado (pendiente > 15°).",
                    )
                )
        return ok

    kept = reachable_pois(kept)
    lm = build_leg_matrix(cm, [hab_rc, *(grid.to_rowcol(p.lat, p.lon) for p in kept)], cfg.energy)
    connected = [k for k in range(1, lm.n) if lm.reachable[0, k] and lm.reachable[k, 0]]
    if len(connected) != lm.n - 1:
        for k in range(1, lm.n):
            if k not in connected:
                p = kept[k - 1]
                discarded.append(
                    Discard(
                        p.poi_id,
                        "unreachable",
                        f"{p.name} no tiene camino de ida y vuelta al hábitat.",
                    )
                )
        kept = [kept[k - 1] for k in connected]
        lm = build_leg_matrix(
            cm, [hab_rc, *(grid.to_rowcol(p.lat, p.lon) for p in kept)], cfg.energy
        )

    front = plan_front(lm, kept, cfg, budget, t_max, seed, pop_size, n_generations)
    plan = MissionPlan(
        front, name_missions(front), discarded, kept, lm, grid, cfg, budget, t_max, radius
    )
    for m in front:
        plan.explanations[m.mission_id] = explain_mission(
            m, lm, kept, cfg, budget, t_max, discarded
        )
    plan.compute_ms = int((time.perf_counter() - t0) * 1000)
    return plan
