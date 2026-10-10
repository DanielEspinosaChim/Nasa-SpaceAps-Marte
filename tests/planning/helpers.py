"""Utilidades de test: mallas de terreno sintético pequeñas y deterministas."""

from __future__ import annotations

import numpy as np
from affine import Affine

from marsmap.geo.coords import M_PER_DEG
from marsmap.planning.costmap import build_costmap
from marsmap.planning.presets import PRESETS, Weights
from marsmap.planning.terrain_grid import TerrainGrid, grid_from_dem

DEG = 200.0 / M_PER_DEG


def make_transform(h, w, lat_top=18.9, lon_left=77.0):
    return Affine(DEG, 0, lon_left, 0, -DEG, lat_top)


def flat_grid(h=30, w=30, elev=-2500.0) -> TerrainGrid:
    return grid_from_dem(np.full((h, w), elev, dtype=np.float32), make_transform(h, w))


def random_grid(h=50, w=50, seed=0) -> TerrainGrid:
    """Relieve ondulado con tramos seguros, de riesgo y bloqueados."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    z = np.zeros((h, w))
    for _ in range(6):
        cy, cx, s = rng.uniform(0, h), rng.uniform(0, w), rng.uniform(4, 10)
        z += rng.uniform(-300, 300) * np.exp(-(((yy - cy) / s) ** 2 + ((xx - cx) / s) ** 2))
    z += rng.normal(0, 4, (h, w))
    return grid_from_dem((z - 2500).astype(np.float32), make_transform(h, w))


def free_cells(cm) -> list[tuple[int, int]]:
    rr, cc = np.nonzero(~cm.blocked)
    return list(zip(rr.tolist(), cc.tolist(), strict=True))


def costmap(grid, preset="balanced", **kw):
    w = PRESETS[preset] if isinstance(preset, str) else preset
    return build_costmap(grid, w, **kw)


ZERO_WEIGHTS = Weights(slope=0, rough=0, risk=0, science=0)
