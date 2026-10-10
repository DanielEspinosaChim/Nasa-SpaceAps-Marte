"""Grafo disperso del mapa de costos (mismas aristas y pesos que A*) para Dijkstra multi-fuente."""

from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra as sp_dijkstra

from marsmap.planning.costmap import OFFSETS, CostMap, step_hdist


def build_graph(cm: CostMap) -> csr_matrix:
    h, w = cm.shape
    rows_idx, cols_idx = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
    free = ~cm.blocked
    src_parts, dst_parts, wt_parts = [], [], []
    for dr, dc in OFFSETS:
        r0, r1 = max(0, -dr), min(h, h - dr)
        c0, c1 = max(0, -dc), min(w, w - dc)
        a_r = rows_idx[r0:r1, c0:c1]
        a_c = cols_idx[r0:r1, c0:c1]
        b_r, b_c = a_r + dr, a_c + dc
        ok = free[a_r, a_c] & free[b_r, b_c]
        if dr and dc:
            ok &= ~(cm.blocked[a_r, b_c] & cm.blocked[b_r, a_c])
        a_r, a_c, b_r, b_c = a_r[ok], a_c[ok], b_r[ok], b_c[ok]
        d = step_hdist(cm, dr, dc, a_r)
        dz = cm.elev[b_r, b_c] - cm.elev[a_r, a_c]
        wt = np.sqrt(d * d + dz * dz) * cm.mult[b_r, b_c]
        src_parts.append(a_r * w + a_c)
        dst_parts.append(b_r * w + b_c)
        wt_parts.append(wt)
    src = np.concatenate(src_parts)
    dst = np.concatenate(dst_parts)
    wt = np.concatenate(wt_parts)
    return csr_matrix((wt, (src, dst)), shape=(h * w, h * w))


def multi_source(graph: csr_matrix, sources: list[int]):
    """Distancias y predecesores desde cada fuente (N búsquedas en C)."""
    return sp_dijkstra(graph, directed=True, indices=sources, return_predecessors=True)


def reconstruct(pred_row: np.ndarray, source: int, target: int, width: int):
    """Camino [(r, c)…] de source a target, o None si no hay camino."""
    cells, cur = [], target
    while cur != source:
        cells.append(divmod(int(cur), width))
        cur = pred_row[cur]
        if cur < 0:
            return None
    cells.append(divmod(int(source), width))
    cells.reverse()
    return cells
