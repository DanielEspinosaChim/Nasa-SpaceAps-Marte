"""NSGA-II: frente de Pareto de misiones (qué POI visitar y en qué orden)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.optimize import minimize
from pymoo.termination.collection import TerminationCollection
from pymoo.termination.max_gen import MaximumGenerationTermination
from pymoo.termination.max_time import TimeBasedTermination

from marsmap.planning.mission.config import MissionConfig
from marsmap.planning.mission.encoding import encode
from marsmap.planning.mission.legs import LegMatrix
from marsmap.planning.mission.objectives import MissionMetrics, evaluate_sequence
from marsmap.planning.mission.poi import PointOfInterest
from marsmap.planning.mission.problem import MissionProblem


@dataclass
class Mission:
    mission_id: str
    sequence: tuple[int, ...]  # nodos 1..N
    metrics: MissionMetrics


def dominates(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return all(x <= y + 1e-12 for x, y in zip(a, b, strict=True)) and any(
        x < y - 1e-12 for x, y in zip(a, b, strict=True)
    )


def pareto_filter(items: list[tuple[tuple[int, ...], MissionMetrics]]):
    """Quita secuencias duplicadas y soluciones dominadas."""
    unique = list({seq: (seq, m) for seq, m in items}.values())
    objs = [m.objectives() for _, m in unique]
    return [
        unique[i]
        for i in range(len(unique))
        if not any(dominates(objs[j], objs[i]) for j in range(len(unique)) if j != i)
    ]


def crowding_trim(items, k: int):
    """Se queda con las k soluciones más dispersas (distancia de crowding)."""
    if len(items) <= k:
        return items
    F = np.array([m.objectives() for _, m in items])
    span = np.where(np.ptp(F, axis=0) > 0, np.ptp(F, axis=0), 1.0)
    Fn = (F - F.min(axis=0)) / span
    dist = np.zeros(len(items))
    for j in range(F.shape[1]):
        order = np.argsort(Fn[:, j], kind="stable")
        dist[order[0]] = dist[order[-1]] = np.inf
        gaps = Fn[order[2:], j] - Fn[order[:-2], j]
        dist[order[1:-1]] += gaps
    keep = sorted(np.argsort(-dist, kind="stable")[:k])
    return [items[i] for i in keep]


def _seed_population(n: int, pop_size: int, rng: np.random.Generator) -> np.ndarray:
    """Población inicial aleatoria con las misiones de un solo POI como semilla."""
    X = rng.uniform(0.0, 1.0, size=(pop_size, n))
    for k in range(min(n, pop_size)):
        X[k] = encode((k + 1,), n, rng)
    return X


def plan_front(
    lm: LegMatrix,
    pois: list[PointOfInterest],
    cfg: MissionConfig,
    energy_budget_wh: float,
    max_time_h: float,
    seed: int = 42,
    pop_size: int | None = None,
    n_generations: int | None = None,
) -> list[Mission]:
    ga = cfg.ga
    pop_size = pop_size or ga.pop_size
    n_generations = n_generations or ga.n_generations
    n = len(pois)
    problem = MissionProblem(lm, pois, cfg, energy_budget_wh, max_time_h)

    if n >= 2:
        rng = np.random.default_rng(seed)
        algorithm = NSGA2(
            pop_size=pop_size,
            sampling=_seed_population(n, pop_size, rng),
            crossover=SBX(prob=0.9, eta=15),
            mutation=PM(eta=20),
            eliminate_duplicates=True,
        )
        termination = TerminationCollection(
            MaximumGenerationTermination(n_generations), TimeBasedTermination(max_time=ga.timeout_s)
        )
        minimize(problem, algorithm, termination, seed=seed, verbose=False)
    elif n == 1:
        problem.resolve((1,))

    # Archivo externo: todo lo evaluado (decodificado y mejorado), factible y no vacío.
    candidates = [
        (seq, m)
        for seq, m in problem._cache.values()  # noqa: SLF001
        if seq and m.feasible(energy_budget_wh, max_time_h)
    ]
    front = pareto_filter(candidates)
    # Misiones con objetivos idénticos (mismas paradas en otro orden) no aportan: se deja una.
    seen: set[tuple[float, ...]] = set()
    unique = []
    for seq, m in sorted(front, key=lambda it: it[0]):
        key = tuple(round(v, 6) for v in m.objectives())
        if key not in seen:
            seen.add(key)
            unique.append((seq, m))
    front = unique
    if not front:
        empty = ()
        front = [(empty, evaluate_sequence(empty, lm, pois, cfg))]
    front = crowding_trim(front, ga.max_front_size)
    front.sort(key=lambda it: (-it[1].science_total, it[1].time_h, it[1].risk_score, it[0]))
    return [Mission(f"m{i:02d}", seq, m) for i, (seq, m) in enumerate(front)]
