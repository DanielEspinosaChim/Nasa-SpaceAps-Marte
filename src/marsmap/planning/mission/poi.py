"""Puntos de interés (POI): modelo y carga desde GeoJSON."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from marsmap.geo.coords import normalize_lon


class PointOfInterest(BaseModel):
    poi_id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=120)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    science_value: float = Field(ge=0, le=1)
    dwell_time_h: float = Field(ge=0, le=12)
    category: str = "other"
    rationale: str = ""
    source: str = "aproximado"
    # Campos opcionales de los sitios reales de muestras de Mars 2020.
    sol: str = ""
    location: str = ""
    sample_type: str = ""
    rock_type: str = ""


def pois_from_dicts(items: list[dict]) -> list[PointOfInterest]:
    pois = [PointOfInterest(**{**p, "lon": normalize_lon(p["lon"])}) for p in items]
    ids = [p.poi_id for p in pois]
    if len(ids) != len(set(ids)):
        raise ValueError("poi_id duplicado")
    return pois


def load_pois(path: Path) -> list[PointOfInterest]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    items = []
    for feat in data.get("features", []):
        lon, lat = feat["geometry"]["coordinates"][:2]
        items.append({**(feat.get("properties") or {}), "lat": lat, "lon": lon})
    return pois_from_dicts(items)


def pois_to_geojson(pois: list[PointOfInterest], meta: dict | None = None) -> dict:
    return {
        "type": "FeatureCollection",
        **(meta or {}),
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [p.lon, p.lat]},
                "properties": p.model_dump(exclude={"lat", "lon"}),
            }
            for p in pois
        ],
    }
