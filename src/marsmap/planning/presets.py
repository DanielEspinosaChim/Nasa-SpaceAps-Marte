"""Presets de pesos del mapa de costos (valores iniciales; se recalibran con el DEM real)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Weights(BaseModel):
    slope: float = Field(ge=0, le=10)
    rough: float = Field(ge=0, le=10)
    risk: float = Field(ge=0, le=10)
    science: float = Field(default=0.0, ge=0, le=10)


PRESETS: dict[str, Weights] = {
    "safe": Weights(slope=4.0, rough=2.0, risk=6.0, science=0.0),
    "fast": Weights(slope=0.5, rough=0.2, risk=1.0, science=0.0),
    "science": Weights(slope=1.5, rough=0.8, risk=3.0, science=1.0),
    "balanced": Weights(slope=2.0, rough=1.0, risk=3.0, science=0.0),
}

PRESET_LABELS = {
    "safe": "Segura",
    "fast": "Rápida",
    "science": "Científica",
    "balanced": "Balanceada",
}
