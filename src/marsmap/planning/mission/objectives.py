"""Evaluación de una misión (secuencia de POI) contra la matriz de tramos."""

from __future__ import annotations

from dataclasses import dataclass

from marsmap.planning.mission.config import MissionConfig
from marsmap.planning.mission.legs import LegMatrix
from marsmap.planning.mission.poi import PointOfInterest


@dataclass(frozen=True)
class MissionMetrics:
    science_total: float
    time_h: float
    energy_wh: float
    risk_m: float
    risk_score: float
    distance_m: float
    max_slope_deg: float
    n_missing_legs: int

    def objectives(self) -> tuple[float, float, float]:
        """Vector a minimizar: (−ciencia, tiempo, riesgo)."""
        return (-self.science_total, self.time_h, self.risk_score)

    def feasible(self, cfg_energy_budget: float, cfg_max_time: float) -> bool:
        return (
            self.n_missing_legs == 0
            and self.energy_wh <= cfg_energy_budget + 1e-9
            and self.time_h <= cfg_max_time + 1e-9
        )


def evaluate_sequence(
    seq: tuple[int, ...], lm: LegMatrix, pois: list[PointOfInterest], cfg: MissionConfig
) -> MissionMetrics:
    """`seq` usa índices de nodo 1..N (el hábitat es el nodo 0 y no se incluye)."""
    nodes = (0, *seq, 0)
    time_h = energy = risk = dist = 0.0
    max_slope = 0.0
    missing = 0
    for a, b in zip(nodes[:-1], nodes[1:], strict=True):
        if not lm.reachable[a, b]:
            missing += 1
            continue
        time_h += lm.time_h[a, b]
        energy += lm.energy_wh[a, b]
        risk += lm.risk_m[a, b]
        dist += lm.distance_m[a, b]
        max_slope = max(max_slope, lm.max_slope_deg[a, b])
    science = dwell = 0.0
    for k in seq:
        science += pois[k - 1].science_value
        dwell += pois[k - 1].dwell_time_h
    time_h += dwell
    energy += cfg.energy.dwell_wh(dwell)
    return MissionMetrics(
        science, time_h, energy, risk, cfg.risk.score(risk, max_slope), dist, max_slope, missing
    )
