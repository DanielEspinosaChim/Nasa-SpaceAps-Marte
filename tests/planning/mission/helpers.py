"""Escenarios sintéticos deterministas para las pruebas de misión."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from shapely.geometry import Polygon

from marsmap.geo.coords import M_PER_DEG
from marsmap.planning.constraints import forbidden_mask
from marsmap.planning.mission.config import load_config
from marsmap.planning.mission.poi import PointOfInterest, pois_from_dicts
from marsmap.planning.mission.service import plan_missions
from marsmap.planning.terrain_grid import TerrainGrid, grid_from_dem
from marsmap.terrain.synthetic import generate_dem, generate_pois

BB = (77.0, 18.0, 77.4, 18.4)
HABITAT = (18.2, 77.2)  # (lat, lon)
CFG = load_config()


@lru_cache(maxsize=4)
def grid_for(seed: int = 1, bbox: tuple = BB) -> TerrainGrid:
    z, t, _, _ = generate_dem(bbox, seed=seed)
    return grid_from_dem(z, t)


def make_pois(grid: TerrainGrid, n: int, seed: int, bbox: tuple = BB) -> list[PointOfInterest]:
    """n POI sintéticos situados en celdas no bloqueadas del terreno (los primeros que quepan)."""
    out = []
    for p in generate_pois(bbox, n * 6, seed=seed):
        rc = grid.to_rowcol(p["lat"], p["lon"])
        if rc is not None and grid.traversability[rc] == 0:
            out.append(p)
        if len(out) == n:
            break
    return pois_from_dicts(out)


def circle_zone(lat, lon, radius_m, buffer_m=0.0, name="rsl"):
    kx = M_PER_DEG * np.cos(np.radians(lat))
    t = np.linspace(0, 2 * np.pi, 181)
    ring = [(lon + radius_m * np.cos(a) / kx, lat + radius_m * np.sin(a) / M_PER_DEG) for a in t]
    return {"name": name, "buffer_m": buffer_m, "geometry": Polygon(ring)}


def run(
    seed=0, n=7, terrain_seed=1, zones=None, budget=12000.0, max_time=720.0, radius=20000.0, **kw
):
    grid = grid_for(terrain_seed)
    pois = make_pois(grid, n, seed)
    return plan_missions(
        grid, HABITAT, pois, zones or [], CFG,
        energy_budget_wh=budget, max_time_h=max_time, max_radius_m=radius, seed=3, **kw,
    )  # fmt: skip


def forbidden_and_outside(plan, zones, habitat=HABITAT, radius=20000.0):
    from marsmap.geo.coords import great_circle_m

    lat, lon = plan.grid.cell_centers()
    outside = great_circle_m(habitat[0], habitat[1], lat, lon) > radius
    return forbidden_mask(plan.grid, zones), outside
