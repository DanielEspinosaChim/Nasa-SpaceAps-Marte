"""Registro de regiones de demostración (`regions.yaml`) con validación."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from marsmap.geo.coords import normalize_lon

REGIONS_FILE = Path(__file__).with_name("regions.yaml")
ID_PATTERN = r"^[a-z0-9_]+$"


class Region(BaseModel):
    region_id: str = Field(pattern=ID_PATTERN)
    name: str = Field(min_length=1)
    bbox: tuple[float, float, float, float]
    description: str = ""

    @field_validator("bbox")
    @classmethod
    def _check_bbox(cls, bbox: tuple[float, float, float, float]):
        return validate_bbox(bbox)


def validate_bbox(bbox) -> tuple[float, float, float, float]:
    """Normaliza longitudes a −180..180 y valida rangos y orden."""
    if len(bbox) != 4:
        raise ValueError("bbox debe tener 4 valores [lon_min, lat_min, lon_max, lat_max]")
    lon_min, lat_min, lon_max, lat_max = (float(v) for v in bbox)
    if not (-90 <= lat_min <= 90 and -90 <= lat_max <= 90):
        raise ValueError("latitudes fuera de rango [-90, 90]")
    if lat_min >= lat_max:
        raise ValueError("lat_min debe ser menor que lat_max")
    for lon in (lon_min, lon_max):
        if not -180 <= lon <= 360:
            raise ValueError("longitudes fuera de rango [-180, 360]")
    lon_min, lon_max = normalize_lon(lon_min), normalize_lon(lon_max)
    if lon_min >= lon_max:
        raise ValueError("lon_min debe ser menor que lon_max (no se admiten bbox que crucen 180°)")
    return (lon_min, lat_min, lon_max, lat_max)


def load_regions(path: Path = REGIONS_FILE) -> dict[str, Region]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    regions = [Region(**r) for r in data.get("regions", [])]
    ids = [r.region_id for r in regions]
    if len(ids) != len(set(ids)):
        raise ValueError("region_id duplicado en regions.yaml")
    return {r.region_id: r for r in regions}


def get_region(region_id: str, path: Path = REGIONS_FILE) -> Region:
    regions = load_regions(path)
    if region_id not in regions:
        raise KeyError(f"región desconocida: {region_id!r}")
    return regions[region_id]
