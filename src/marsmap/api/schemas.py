"""Modelos Pydantic de entrada y salida de la API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from marsmap.geo.coords import normalize_lon
from marsmap.planning.presets import Weights

ID_RE = r"^[a-z0-9_]+$"


class ErrorOut(BaseModel):
    error: str
    code: str


class RegionOut(BaseModel):
    region_id: str
    name: str
    bbox: list[float]
    description: str = ""


class LegendItem(BaseModel):
    value: float
    color: str
    label: str


class LayerOut(BaseModel):
    layer_id: str
    name: str
    units: str
    source_dataset: str
    instrument: str
    resolution_m: float
    crs: str
    bbox: list[float]
    generated_at: str
    limitations: str
    legend: list[LegendItem]
    image_url: str


class CellOut(BaseModel):
    lat: float
    lon: float
    elevation_m: float | None
    slope_deg: float | None
    roughness_m: float | None
    traversability: int | None


class LatLon(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=360)

    @field_validator("lon")
    @classmethod
    def _norm(cls, v: float) -> float:
        return normalize_lon(v)


# ---- Ruta (003) ----------------------------------------------------------------------------


class RouteRequest(BaseModel):
    start: LatLon
    goal: LatLon
    preset: Literal["safe", "fast", "science", "balanced"] | None = None
    weights: Weights | None = None
    habitat: LatLon | None = None
    max_radius_m: float | None = Field(default=None, gt=0, le=100_000)
    use_forbidden_zones: bool = True

    @model_validator(mode="after")
    def _radius_needs_habitat(self):
        if self.max_radius_m is not None and self.habitat is None:
            raise ValueError("max_radius_m requiere habitat")
        return self


class ProfilePoint(BaseModel):
    d_m: float
    elev_m: float
    risk: bool = False


class LineString(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]]


class RouteOut(BaseModel):
    status: Literal["ok", "no_route"]
    reason: str | None = None
    geometry: LineString | None = None
    distance_m: float | None = None
    straight_line_m: float | None = None
    tortuosity: float | None = None
    max_slope_deg: float | None = None
    mean_slope_deg: float | None = None
    elevation_gain_m: float | None = None
    elevation_loss_m: float | None = None
    pct_risk_cells: float | None = None
    est_time_h: float | None = None
    profile: list[ProfilePoint] = []
    explanations: list[str] = []
    weights_used: Weights
    compute_ms: int


class PresetOut(BaseModel):
    preset: str
    label: str
    weights: Weights


# ---- Misión (004) --------------------------------------------------------------------------


class MissionRequest(BaseModel):
    habitat: LatLon
    poi_ids: list[str] | None = Field(default=None, max_length=20)
    energy_budget_wh: float | None = Field(default=None, gt=0, le=50_000)
    max_time_h: float | None = Field(default=None, gt=0, le=720)
    max_radius_m: float | None = Field(default=None, gt=0, le=100_000)
    use_forbidden_zones: bool = True
    seed: int = Field(default=42, ge=0, lt=2**31)
    pop_size: int | None = Field(default=None, ge=20, le=200)
    n_generations: int | None = Field(default=None, ge=10, le=300)

    @field_validator("poi_ids")
    @classmethod
    def _ids(cls, v):
        import re

        if v is not None and any(not re.fullmatch(ID_RE, i) or len(i) > 64 for i in v):
            raise ValueError("poi_id inválido")
        return v


class LegOut(BaseModel):
    from_: str = Field(alias="from")
    to: str
    distance_m: float
    time_h: float
    energy_wh: float
    risk_m: float
    max_slope_deg: float
    coordinates: list[list[float]] = []

    model_config = {"populate_by_name": True}


class MissionOut(BaseModel):
    mission_id: str
    sequence: list[str]
    geometry: LineString
    legs: list[LegOut]
    science_total: float
    time_h: float
    energy_wh: float
    risk_m: float
    risk_score: float
    distance_m: float
    max_slope_deg: float
    explanations: list[str]


class DiscardOut(BaseModel):
    poi_id: str
    reason_code: str
    reason: str


class MissionResultOut(BaseModel):
    result_id: str
    front: list[MissionOut]
    named: dict[str, str]
    discarded: list[DiscardOut]
    params_used: dict
    limitations: list[str]
    compute_ms: int


class SelectRequest(BaseModel):
    safety: float = Field(ge=0, le=1)
    science: float = Field(ge=0, le=1)
    speed: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _some_positive(self):
        if self.safety + self.science + self.speed <= 0:
            raise ValueError("al menos un peso debe ser mayor que 0")
        return self
