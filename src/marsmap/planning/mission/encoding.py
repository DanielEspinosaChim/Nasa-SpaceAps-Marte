"""Codificación por claves aleatorias: un real en [0,1] por POI.

Un POI se visita si su clave es ≥ 0.5; los visitados se ordenan por clave
descendente. Toda solución decodifica a una secuencia válida en estructura.
"""

from __future__ import annotations

import numpy as np

THRESHOLD = 0.5
INF_TIME = 1e9


def decode(keys: np.ndarray) -> tuple[int, ...]:
    """Claves → secuencia de nodos 1..N (índice de POI + 1)."""
    keys = np.asarray(keys)
    visited = np.nonzero(keys >= THRESHOLD)[0]
    order = visited[np.argsort(-keys[visited], kind="stable")]
    return tuple(int(i) + 1 for i in order)


def encode(seq: tuple[int, ...], n: int, rng: np.random.Generator) -> np.ndarray:
    """Secuencia → claves (inversa de `decode`); los no visitados reciben claves < 0.5."""
    keys = rng.uniform(0.0, THRESHOLD - 1e-3, size=n)
    k = len(seq)
    for pos, node in enumerate(seq):
        keys[node - 1] = THRESHOLD + (1.0 - THRESHOLD) * (k - pos) / (k + 1)
    return keys


def tour_time(seq, time_matrix) -> float:
    nodes = (0, *seq, 0)
    return sum(time_matrix[a][b] for a, b in zip(nodes[:-1], nodes[1:], strict=True))


def two_opt(seq: tuple[int, ...], time_matrix) -> tuple[int, ...]:
    """2-opt sobre el tiempo de recorrido. Nunca empeora la secuencia de entrada."""
    best = list(seq)
    if len(best) < 2:
        return tuple(best)
    best_t = tour_time(best, time_matrix)
    improved = True
    while improved:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                cand = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                t = tour_time(cand, time_matrix)
                if t < best_t - 1e-12:
                    best, best_t, improved = cand, t, True
    return tuple(best)


def time_matrix_for_search(time_h: np.ndarray, reachable: np.ndarray) -> list[list[float]]:
    """Matriz de tiempos como listas (rápida en Python); tramos sin camino = INF_TIME."""
    t = np.where(reachable, time_h, INF_TIME)
    return t.tolist()
