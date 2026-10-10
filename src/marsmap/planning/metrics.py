"""Métricas de una ruta: distancia 3D, tortuosidad, pendientes, desnivel, perfil y tiempo."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from marsmap.geo.coords import great_circle_m
from marsmap.planning.costmap import CostMap

SPEED_SAFE_M_H = 100.0
SPEED_RISK_M_H = 50.0
MAX_PROFILE_POINTS = 500


@dataclass
class RouteMetrics:
    distance_m: float
    horizontal_m: float
    straight_line_m: float
    tortuosity: float
    max_slope_deg: float
    mean_slope_deg: float
    elevation_gain_m: float
    elevation_loss_m: float
    pct_risk_cells: float
    risk_m: float
    est_time_h: float
    profile: list[dict]


def step_arrays(cm: CostMap, cells: list[tuple[int, int]]):
    """Por paso: distancia horizontal, distancia 3D, desnivel y si el destino es de riesgo."""
    arr = np.asarray(cells)
    if len(arr) < 2:
        z = np.zeros(0)
        return z, z, z, np.zeros(0, dtype=bool)
    a, b = arr[:-1], arr[1:]
    hd = np.hypot((b[:, 1] - a[:, 1]) * cm.dx_m[a[:, 0]], (b[:, 0] - a[:, 0]) * cm.dy_m)
    dz = cm.elev[b[:, 0], b[:, 1]] - cm.elev[a[:, 0], a[:, 1]]
    return hd, np.sqrt(hd * hd + dz * dz), dz, cm.risk[b[:, 0], b[:, 1]]


def compute_metrics(cm: CostMap, cells: list[tuple[int, int]]) -> RouteMetrics:
    hd, d3, dz, step_risk = step_arrays(cm, cells)
    arr = np.asarray(cells)
    slopes = cm.slope[arr[:, 0], arr[:, 1]]
    lat0, lon0 = cm.grid.to_lonlat(*cells[0])[::-1]
    lat1, lon1 = cm.grid.to_lonlat(*cells[-1])[::-1]
    straight = float(great_circle_m(lat0, lon0, lat1, lon1))
    dist = float(d3.sum())
    speed = np.where(step_risk, SPEED_RISK_M_H, SPEED_SAFE_M_H)
    cum = np.concatenate([[0.0], np.cumsum(d3)])
    elev = cm.elev[arr[:, 0], arr[:, 1]]
    idx = np.unique(np.linspace(0, len(cum) - 1, min(len(cum), MAX_PROFILE_POINTS)).astype(int))
    return RouteMetrics(
        distance_m=dist,
        horizontal_m=float(hd.sum()),
        straight_line_m=straight,
        tortuosity=dist / straight if straight > 0 else 1.0,
        max_slope_deg=float(slopes.max()),
        mean_slope_deg=float(slopes.mean()),
        elevation_gain_m=float(dz[dz > 0].sum()),
        elevation_loss_m=float(-dz[dz < 0].sum()),
        pct_risk_cells=100.0 * float(cm.risk[arr[:, 0], arr[:, 1]].mean()),
        risk_m=float(d3[step_risk].sum()),
        est_time_h=float((d3 / speed).sum()),
        profile=[
            {
                "d_m": float(cum[i]),
                "elev_m": float(elev[i]),
                "risk": bool(cm.risk[arr[i, 0], arr[i, 1]]),
            }
            for i in idx
        ],
    )


def straight_line_cells(a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
    """Celdas bajo el segmento a→b (Bresenham)."""
    (r0, c0), (r1, c1) = a, b
    n = max(abs(r1 - r0), abs(c1 - c0))
    if n == 0:
        return [a]
    rr = np.rint(np.linspace(r0, r1, n + 1)).astype(int)
    cc = np.rint(np.linspace(c0, c1, n + 1)).astype(int)
    return list(zip(rr.tolist(), cc.tolist(), strict=True))
