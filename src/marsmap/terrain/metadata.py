"""Metadatos de capa (`metadata.json`): fuente, instrumento, resolución y limitaciones."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

METADATA_FILE = "metadata.json"


class LayerMetadata(BaseModel):
    layer_id: str = Field(pattern=r"^[a-z_]+$")
    name: str
    units: str = Field(min_length=1)
    file: str = Field(pattern=r"^[a-z_]+\.tif$")
    source_dataset: str
    instrument: str
    resolution_m: float = Field(gt=0)
    crs: str
    bbox: tuple[float, float, float, float]
    generated_at: str
    limitations: str

    @field_validator("bbox")
    @classmethod
    def _lon_range(cls, bbox):
        lon_min, lat_min, lon_max, lat_max = bbox
        if not (-180 <= lon_min < lon_max <= 180 and -90 <= lat_min < lat_max <= 90):
            raise ValueError("bbox inválido o con longitudes fuera de −180..180")
        return bbox


class RegionMetadata(BaseModel):
    region_id: str = Field(pattern=r"^[a-z0-9_]+$")
    width: int
    height: int
    layers: list[LayerMetadata]


def now_iso() -> str:
    """Fecha ISO 8601 UTC. Respeta SOURCE_DATE_EPOCH para builds reproducibles."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    dt = datetime.fromtimestamp(int(epoch), UTC) if epoch else datetime.now(UTC)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_metadata(folder: Path, meta: RegionMetadata) -> Path:
    path = folder / METADATA_FILE
    path.write_text(
        json.dumps(meta.model_dump(mode="json"), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return path


def read_metadata(folder: Path) -> RegionMetadata:
    return RegionMetadata.model_validate_json((folder / METADATA_FILE).read_text(encoding="utf-8"))
