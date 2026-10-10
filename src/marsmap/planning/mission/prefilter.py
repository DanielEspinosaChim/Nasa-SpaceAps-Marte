"""Descartes previos a la optimización: walkback, zonas prohibidas y puntos inalcanzables."""

from __future__ import annotations

from dataclasses import dataclass

from marsmap.geo.coords import great_circle_m
from marsmap.planning.constraints import zone_at
from marsmap.planning.mission.poi import PointOfInterest
from marsmap.planning.terrain_grid import TerrainGrid


@dataclass(frozen=True)
class Discard:
    poi_id: str
    reason_code: str  # outside_walkback | forbidden_zone | unreachable
    reason: str


def prefilter(
    pois: list[PointOfInterest],
    grid: TerrainGrid,
    zones: list[dict],
    habitat: tuple[float, float],
    max_radius_m: float,
) -> tuple[list[PointOfInterest], list[Discard]]:
    """`habitat` es (lat, lon). Devuelve (POI que pasan, descartes con su razón)."""
    kept, out = [], []
    for p in pois:
        d = float(great_circle_m(habitat[0], habitat[1], p.lat, p.lon))
        zone = zone_at(grid, zones, p.lat, p.lon) if zones else None
        if grid.to_rowcol(p.lat, p.lon) is None:
            out.append(
                Discard(
                    p.poi_id, "unreachable", f"{p.name} queda fuera de la región cartografiada."
                )
            )
        elif zone:
            out.append(
                Discard(
                    p.poi_id,
                    "forbidden_zone",
                    f"{p.name} está dentro de la zona prohibida «{zone}».",
                )
            )
        elif d > max_radius_m:
            out.append(
                Discard(
                    p.poi_id,
                    "outside_walkback",
                    f"{p.name} está a {d / 1000:.1f} km del hábitat, más allá del límite de "
                    f"walkback de {max_radius_m / 1000:.1f} km.",
                )
            )
        else:
            kept.append(p)
    return kept, out
