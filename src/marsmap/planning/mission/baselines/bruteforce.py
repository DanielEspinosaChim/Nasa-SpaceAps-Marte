"""Fuerza bruta (N ≤ 8): la misión factible de mayor valor científico, probando todos los órdenes."""

from __future__ import annotations

from marsmap.planning.mission.config import MissionConfig
from marsmap.planning.mission.legs import LegMatrix
from marsmap.planning.mission.poi import PointOfInterest


def best_science(
    lm: LegMatrix,
    pois: list[PointOfInterest],
    cfg: MissionConfig,
    energy_budget_wh: float,
    max_time_h: float,
) -> tuple[tuple[int, ...], float]:
    n = len(pois)
    if n > 8:
        raise ValueError("fuerza bruta solo para N ≤ 8")
    best_seq: tuple[int, ...] = ()
    best_sci = 0.0

    def dfs(cur: int, seq: list[int], energy: float, time_h: float, science: float) -> None:
        nonlocal best_seq, best_sci
        if seq and lm.reachable[cur, 0]:
            e = energy + lm.energy_wh[cur, 0]
            t = time_h + lm.time_h[cur, 0]
            if (
                e <= energy_budget_wh + 1e-9
                and t <= max_time_h + 1e-9
                and science > best_sci + 1e-12
            ):
                best_seq, best_sci = tuple(seq), science
        for k in range(1, n + 1):
            if k in seq or not lm.reachable[cur, k]:
                continue
            p = pois[k - 1]
            e = energy + lm.energy_wh[cur, k] + cfg.energy.dwell_wh(p.dwell_time_h)
            t = time_h + lm.time_h[cur, k] + p.dwell_time_h
            if e > energy_budget_wh or t > max_time_h:
                continue  # los costos solo crecen: poda segura
            seq.append(k)
            dfs(k, seq, e, t, science + p.science_value)
            seq.pop()

    dfs(0, [], 0.0, 0.0, 0.0)
    return best_seq, best_sci
