"""A* sobre el mapa de costos (8 vecinos, heurística admisible, timeout)."""

from __future__ import annotations

import heapq
import math
import time
from dataclasses import dataclass

from marsmap.planning.costmap import OFFSETS, CostMap, step_hdist


class SearchTimeout(Exception):
    """La búsqueda superó el tiempo máximo permitido."""


@dataclass
class PathResult:
    cells: list[tuple[int, int]]
    cost: float
    expanded: int


def search(
    cm: CostMap,
    start: tuple[int, int],
    goal: tuple[int, int],
    use_heuristic: bool = True,
    timeout_s: float | None = 5.0,
) -> PathResult | None:
    h, w = cm.shape
    sidx, gidx = cm.idx(*start), cm.idx(*goal)
    if cm.blocked[start] or cm.blocked[goal]:
        return None
    if sidx == gidx:
        return PathResult([start], 0.0, 0)

    mult = cm.mult.ravel().tolist()
    blocked = cm.blocked.ravel().tolist()
    elev = cm.elev.ravel().tolist()
    hd = {
        (dr, dc): step_hdist(cm, dr, dc, slice(None)).tolist() for dr, dc in OFFSETS
    }  # distancia horizontal por fila de origen
    gr, gc = goal
    dx_min = float(cm.dx_m.min())
    dy = cm.dy_m
    hmin = cm.min_mult if use_heuristic else 0.0

    def heur(r: int, c: int) -> float:
        return hmin * math.hypot((c - gc) * dx_min, (r - gr) * dy)

    inf = math.inf
    g = [inf] * (h * w)
    parent = [-1] * (h * w)
    closed = [False] * (h * w)
    g[sidx] = 0.0
    heap = [(heur(*start), sidx)]
    deadline = None if timeout_s is None else time.perf_counter() + timeout_s
    expanded = 0
    sqrt = math.sqrt

    while heap:
        _, a = heapq.heappop(heap)
        if closed[a]:
            continue
        closed[a] = True
        if a == gidx:
            break
        expanded += 1
        if deadline is not None and expanded & 255 == 0 and time.perf_counter() > deadline:
            raise SearchTimeout(f"búsqueda cancelada tras {timeout_s:.1f} s")
        r, c = divmod(a, w)
        ga, za = g[a], elev[a]
        for dr, dc in OFFSETS:
            nr, nc = r + dr, c + dc
            if nr < 0 or nr >= h or nc < 0 or nc >= w:
                continue
            b = nr * w + nc
            if blocked[b] or closed[b]:
                continue
            if dr and dc and (blocked[r * w + nc] and blocked[nr * w + c]):
                continue
            dz = elev[b] - za
            d = hd[(dr, dc)][r]
            ng = ga + sqrt(d * d + dz * dz) * mult[b]
            if ng < g[b]:
                g[b] = ng
                parent[b] = a
                heapq.heappush(heap, (ng + heur(nr, nc), b))

    if not closed[gidx]:
        return None
    cells, cur = [], gidx
    while cur != -1:
        cells.append(divmod(cur, w))
        cur = parent[cur]
    cells.reverse()
    return PathResult(cells, g[gidx], expanded)


def astar(cm: CostMap, start, goal, timeout_s: float | None = 5.0) -> PathResult | None:
    return search(cm, start, goal, use_heuristic=True, timeout_s=timeout_s)
