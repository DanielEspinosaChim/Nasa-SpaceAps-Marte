"""Configuración de misión (YAML) y modelo de energía."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

CONFIG_FILE = Path(__file__).resolve().parents[2] / "config" / "mission_config.yaml"


class EnergyModel(BaseModel):
    e_per_m: float = Field(gt=0)
    e_per_m_up: float = Field(ge=0)
    p_dwell_w: float = Field(ge=0)

    def leg_wh(self, distance_m: float, gain_m: float) -> float:
        return self.e_per_m * distance_m + self.e_per_m_up * gain_m

    def dwell_wh(self, hours: float) -> float:
        return self.p_dwell_w * hours


class RiskModel(BaseModel):
    slope_penalty_start_deg: float = 10.0
    slope_penalty_per_deg: float = 50.0

    def score(self, risk_m: float, max_slope_deg: float) -> float:
        return risk_m + self.slope_penalty_per_deg * max(
            0.0, max_slope_deg - self.slope_penalty_start_deg
        )


class GaParams(BaseModel):
    pop_size: int = Field(default=100, ge=20, le=200)
    n_generations: int = Field(default=200, ge=10, le=300)
    max_front_size: int = Field(default=30, ge=1, le=100)
    timeout_s: float = Field(default=30.0, gt=0, le=120)


class MissionConfig(BaseModel):
    energy: EnergyModel
    energy_budget_wh: float = Field(gt=0, le=50_000)
    max_time_h: float = Field(gt=0, le=720)
    max_radius_m: float = Field(gt=0, le=100_000)
    risk: RiskModel = RiskModel()
    ga: GaParams = GaParams()


def load_config(path: Path = CONFIG_FILE) -> MissionConfig:
    return MissionConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
