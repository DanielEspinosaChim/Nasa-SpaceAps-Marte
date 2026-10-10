"""Restricciones duras rasterizadas: zonas prohibidas con búfer y radio desde el hábitat."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import shape

from marsmap.geo.coords import M_PER_DEG, great_circle_m, normalize_lon
from marsmap.planning.terrain_grid import TerrainGrid


class LocalProjection:
    """Equirectangular local (metros) centrada en la región, para búferes en metros."""

    def __init__(self, lat0: float):
        self.kx = M_PER_DEG * np.cos(np.radians(lat0))
        self.ky = M_PER_DEG

    def fwd(self, lon, lat):
        return np.asarray(lon) * self.kx, np.asarray(lat) * self.ky

    def geom_m(self, geom):
        return shapely.transform(
            geom, lambda a: np.column_stack([a[:, 0] * self.kx, a[:, 1] * self.ky])
        )


def load_forbidden_zones(path: Path) -> list[dict]:
    """Lee un GeoJSON de zonas prohibidas. Cada feature puede traer `buffer_m` y `name`."""
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    zones = []
    for i, feat in enumerate(data.get("features", [])):
        props = feat.get("properties") or {}
        geom = shape(feat["geometry"])
        geom = shapely.transform(
            geom, lambda a: np.column_stack([np.vectorize(normalize_lon)(a[:, 0]), a[:, 1]])
        )
        zones.append(
            {
                "name": str(props.get("name", f"zona_{i + 1}")),
                "buffer_m": float(props.get("buffer_m", 0.0)),
                "geometry": geom,
            }
        )
    return zones


def forbidden_mask(grid: TerrainGrid, zones: list[dict]) -> np.ndarray:
    """True donde la celda cae dentro de una zona prohibida (búfer incluido)."""
    mask = np.zeros(grid.shape, dtype=bool)
    if not zones:
        return mask
    lat, lon = grid.cell_centers()
    proj = LocalProjection(float(lat.mean()))
    x, y = proj.fwd(lon, lat)
    for zone in zones:
        geom_m = proj.geom_m(zone["geometry"])
        if zone["buffer_m"] > 0:
            geom_m = geom_m.buffer(zone["buffer_m"])
        mask |= shapely.contains_xy(geom_m, x, y) | shapely.intersects_xy(geom_m.boundary, x, y)
    return mask


def zone_at(grid: TerrainGrid, zones: list[dict], lat: float, lon: float) -> str | None:
    """Nombre de la zona prohibida que contiene el punto (con búfer), o None."""
    lat_c = float(np.mean(grid.cell_centers()[0]))
    proj = LocalProjection(lat_c)
    x, y = proj.fwd(normalize_lon(lon), lat)
    for zone in zones:
        geom_m = proj.geom_m(zone["geometry"])
        if geom_m.buffer(zone["buffer_m"]).covers(shapely.Point(float(x), float(y))):
            return zone["name"]
    return None


def radius_mask(grid: TerrainGrid, habitat_lat: float, habitat_lon: float, max_radius_m: float):
    """True donde la celda está FUERA del radio máximo desde el hábitat."""
    lat, lon = grid.cell_centers()
    return great_circle_m(habitat_lat, normalize_lon(habitat_lon), lat, lon) > max_radius_m
