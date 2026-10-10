"""Matriz de tramos hábitat/POI: una búsqueda Dijkstra por nodo sobre el grafo de la 003."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from marsmap.planning.costmap import CostMap
from marsmap.planning.graph import build_graph, multi_source, reconstruct
from marsmap.planning.metrics import SPEED_RISK_M_H, SPEED_SAFE_M_H, step_arrays
from marsmap.planning.mission.config import EnergyModel


@dataclass
class LegMatrix:
    """Nodo 0 = hábitat; nodos 1..N = POI. Las matrices son (N+1)×(N+1) y asimétricas."""

    node_rc: list[tuple[int, int]]
    cost: np.ndarray
    distance_m: np.ndarray
    time_h: np.ndarray
    energy_wh: np.ndarray
    gain_m: np.ndarray
    risk_m: np.ndarray
    max_slope_deg: np.ndarray
    reachable: np.ndarray
    paths: dict[tuple[int, int], list[tuple[int, int]]] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.node_rc)


def build_leg_matrix(cm: CostMap, node_rc: list[tuple[int, int]], energy: EnergyModel) -> LegMatrix:
    n = len(node_rc)
    w = cm.shape[1]
    src = [r * w + c for r, c in node_rc]
    dist, pred = multi_source(build_graph(cm), src)
    z = lambda: np.zeros((n, n))  # noqa: E731
    cost, d3m, tim, ene, gain, risk, mslope = (z() for _ in range(7))
    reach = np.zeros((n, n), dtype=bool)
    paths: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for i in range(n):
        for j in range(n):
            if i == j:
                reach[i, j] = True
                continue
            if not np.isfinite(dist[i, src[j]]):
                cost[i, j] = np.inf
                continue
            cells = reconstruct(pred[i], src[i], src[j], w)
            if cells is None:
                cost[i, j] = np.inf
                continue
            _, d3, dz, step_risk = step_arrays(cm, cells)
            arr = np.asarray(cells)
            speed = np.where(step_risk, SPEED_RISK_M_H, SPEED_SAFE_M_H)
            reach[i, j] = True
            paths[(i, j)] = cells
            cost[i, j] = dist[i, src[j]]
            d3m[i, j] = d3.sum()
            tim[i, j] = (d3 / speed).sum()
            gain[i, j] = dz[dz > 0].sum()
            ene[i, j] = energy.leg_wh(d3m[i, j], gain[i, j])
            risk[i, j] = d3[step_risk].sum()
            mslope[i, j] = cm.slope[arr[:, 0], arr[:, 1]].max()
    return LegMatrix(node_rc, cost, d3m, tim, ene, gain, risk, mslope, reach, paths)
