"""Mapa de costos: multiplicador por celda y máscara de bloqueo.

costo(a→b) = d3D(a,b) · mult(b),  con
mult = 1 + w_slope·s + w_rough·r + w_risk·[trav==1]   (s = pendiente/15°, r = rugosidad/p95)
y, si hay valor científico, mult · max(0.5, 1 − 0.5·w_science·interés).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from marsmap.geo.coords import great_circle_m
from marsmap.planning.presets import Weights
from marsmap.planning.terrain_grid import TerrainGrid
from marsmap.terrain.derive import SLOPE_BLOCKED_DEG, TRAV_BLOCKED, TRAV_NODATA, TRAV_RISK

MIN_SCIENCE_FACTOR = 0.5


@dataclass
class CostMap:
    grid: TerrainGrid
    weights: Weights
    mult: np.ndarray  # float64, inf en celdas bloqueadas
    blocked: np.ndarray  # bool
    risk: np.ndarray  # bool: transitabilidad 1
    elev: np.ndarray  # float64
    slope: np.ndarray  # float64 grados
    dx_m: np.ndarray  # (h,) metros Este-Oeste por celda, por fila
    dy_m: float
    min_mult: float

    @property
    def shape(self) -> tuple[int, int]:
        return self.mult.shape

    def idx(self, r: int, c: int) -> int:
        return r * self.shape[1] + c

    def rc(self, idx: int) -> tuple[int, int]:
        return divmod(idx, self.shape[1])


def poi_interest(grid: TerrainGrid, pois: list[dict], radius_m: float = 1500.0) -> np.ndarray:
    """Interés [0,1] por celda: máximo de ciencia·(1 − d/radio) sobre los POI."""
    interest = np.zeros(grid.shape)
    if not pois:
        return interest
    lat, lon = grid.cell_centers()
    for p in pois:
        d = great_circle_m(p["lat"], p["lon"], lat, lon)
        interest = np.maximum(interest, p["science_value"] * np.clip(1 - d / radius_m, 0, 1))
    return interest


def build_costmap(
    grid: TerrainGrid,
    weights: Weights,
    forbidden: np.ndarray | None = None,
    outside_radius: np.ndarray | None = None,
    interest: np.ndarray | None = None,
) -> CostMap:
    elev = grid.elevation
    trav = grid.traversability
    blocked = (trav == TRAV_BLOCKED) | (trav == TRAV_NODATA) | np.isnan(elev)
    if forbidden is not None:
        blocked |= forbidden
    if outside_radius is not None:
        blocked |= outside_radius

    slope = np.nan_to_num(grid.slope, nan=SLOPE_BLOCKED_DEG)
    s = np.clip(slope / SLOPE_BLOCKED_DEG, 0.0, 1.0)
    rough = np.nan_to_num(grid.roughness, nan=0.0)
    finite = rough[~blocked]
    p95 = float(np.percentile(finite, 95)) if finite.size else 0.0
    r = np.clip(rough / p95, 0.0, 1.0) if p95 > 0 else np.zeros_like(rough)
    risk = trav == TRAV_RISK

    mult = 1.0 + weights.slope * s + weights.rough * r + weights.risk * risk
    if interest is not None and weights.science > 0:
        mult = mult * np.maximum(MIN_SCIENCE_FACTOR, 1.0 - 0.5 * weights.science * interest)
    mult = np.where(blocked, np.inf, mult)
    free = mult[~blocked]
    return CostMap(
        grid=grid,
        weights=weights,
        mult=mult,
        blocked=blocked,
        risk=risk,
        elev=np.nan_to_num(elev, nan=0.0).astype(np.float64),
        slope=slope,
        dx_m=grid.dx_m,
        dy_m=grid.dy_m,
        min_mult=float(free.min()) if free.size else 1.0,
    )


# Vecinos (dr, dc). Las diagonales no cruzan esquinas entre dos celdas bloqueadas.
OFFSETS = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]


def step_hdist(cm: CostMap, dr: int, dc: int, row: np.ndarray | int):
    """Distancia horizontal (m) de un paso (dr, dc) desde la(s) fila(s) dadas."""
    return np.hypot(dc * cm.dx_m[row], dr * cm.dy_m)
