"""Baseline voraz: inserción por ciencia/energía, una misión por cada presupuesto de una rejilla."""

from __future__ import annotations

import numpy as np

from marsmap.planning.mission.config import MissionConfig
from marsmap.planning.mission.legs import LegMatrix
from marsmap.planning.mission.objectives import MissionMetrics, evaluate_sequence
from marsmap.planning.mission.optimize import pareto_filter
from marsmap.planning.mission.poi import PointOfInterest


def greedy_missions(
    lm: LegMatrix,
    pois: list[PointOfInterest],
    cfg: MissionConfig,
    energy_budget_wh: float,
    max_time_h: float,
    n_budgets: int = 10,
) -> list[tuple[tuple[int, ...], MissionMetrics]]:
    found = []
    for frac in np.linspace(1.0 / n_budgets, 1.0, n_budgets):
        budget = energy_budget_wh * float(frac)
        seq: list[int] = []
        cur = evaluate_sequence((), lm, pois, cfg)
        while True:
            best = None
            for k in range(1, len(pois) + 1):
                if k in seq:
                    continue
                for pos in range(len(seq) + 1):
                    cand = (*seq[:pos], k, *seq[pos:])
                    m = evaluate_sequence(cand, lm, pois, cfg)
                    if not m.feasible(budget, max_time_h):
                        continue
                    ratio = pois[k - 1].science_value / max(m.energy_wh - cur.energy_wh, 1e-9)
                    if best is None or ratio > best[0]:
                        best = (ratio, cand, m)
            if best is None:
                break
            _, cand, cur = best
            seq = list(cand)
        if seq:
            found.append((tuple(seq), cur))
    return pareto_filter(found)
