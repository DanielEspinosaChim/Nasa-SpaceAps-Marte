"""Problema de optimización multiobjetivo para pymoo (objetivos y restricciones)."""

from __future__ import annotations

import numpy as np
from pymoo.core.problem import Problem

from marsmap.planning.mission.config import MissionConfig
from marsmap.planning.mission.encoding import decode, time_matrix_for_search, two_opt
from marsmap.planning.mission.legs import LegMatrix
from marsmap.planning.mission.objectives import MissionMetrics, evaluate_sequence
from marsmap.planning.mission.poi import PointOfInterest


class MissionProblem(Problem):
    """3 objetivos (−ciencia, tiempo, riesgo) y 3 restricciones (energía, tiempo, tramos sin camino)."""

    def __init__(
        self,
        lm: LegMatrix,
        pois: list[PointOfInterest],
        cfg: MissionConfig,
        energy_budget_wh: float,
        max_time_h: float,
    ):
        super().__init__(n_var=len(pois), n_obj=3, n_ieq_constr=3, xl=0.0, xu=1.0)
        self.lm, self.pois, self.cfg = lm, pois, cfg
        self.energy_budget_wh, self.max_time_h = energy_budget_wh, max_time_h
        self._tm = time_matrix_for_search(lm.time_h, lm.reachable)
        self._cache: dict[tuple[int, ...], tuple[tuple[int, ...], MissionMetrics]] = {}
        # Orden ya pulido por 2-opt de cada conjunto de paradas: el 2-opt es lo más caro, y los
        # órdenes distintos de un mismo conjunto convergen al mismo óptimo local.
        self._polished: dict[frozenset[int], tuple[int, ...]] = {}

    def resolve(self, decoded: tuple[int, ...]) -> tuple[tuple[int, ...], MissionMetrics]:
        """Secuencia decodificada → (secuencia con orden mejorado por 2-opt, métricas). Con caché."""
        hit = self._cache.get(decoded)
        if hit is None:
            seq = self._polished.get(frozenset(decoded))
            if seq is None:
                seq = two_opt(decoded, self._tm)
                self._polished[frozenset(decoded)] = seq
            hit = (seq, evaluate_sequence(seq, self.lm, self.pois, self.cfg))
            self._cache[decoded] = hit
        return hit

    def _evaluate(self, X, out, *args, **kwargs):
        F = np.empty((len(X), 3))
        G = np.empty((len(X), 3))
        for i, keys in enumerate(X):
            _, m = self.resolve(decode(keys))
            F[i] = m.objectives()
            G[i] = (
                m.energy_wh - self.energy_budget_wh,
                m.time_h - self.max_time_h,
                m.n_missing_legs,
            )
        out["F"], out["G"] = F, G
