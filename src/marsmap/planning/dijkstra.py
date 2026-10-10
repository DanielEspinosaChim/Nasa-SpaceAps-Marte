"""Dijkstra de referencia: la misma búsqueda sin heurística (baseline de optimalidad)."""

from __future__ import annotations

from marsmap.planning.astar import PathResult, search
from marsmap.planning.costmap import CostMap


def dijkstra(cm: CostMap, start, goal, timeout_s: float | None = 30.0) -> PathResult | None:
    return search(cm, start, goal, use_heuristic=False, timeout_s=timeout_s)
