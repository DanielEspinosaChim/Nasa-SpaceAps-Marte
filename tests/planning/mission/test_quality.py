"""Calidad del genético frente a la solución exacta (N ≤ 8) y al baseline voraz (hipervolumen)."""

import time

import numpy as np
import pytest
from pymoo.indicators.hv import HV

from marsmap.planning.mission.baselines.bruteforce import best_science
from marsmap.planning.mission.baselines.greedy import greedy_missions
from marsmap.planning.mission.service import plan_missions
from marsmap.planning.terrain_grid import grid_from_dem
from marsmap.terrain.synthetic import generate_dem
from tests.planning.mission.helpers import CFG, HABITAT, grid_for, make_pois, run

BUDGET, MAX_TIME = 9000.0, 720.0


@pytest.mark.slow
def test_science_mission_matches_bruteforce_with_7_pois():
    exact, close = 0, 0
    for seed in range(10):
        plan = run(seed=seed, n=7, budget=BUDGET)
        _, best = best_science(plan.lm, plan.pois, CFG, BUDGET, MAX_TIME)
        got = plan.mission(plan.named["science"]).metrics.science_total
        assert got <= best + 1e-6  # nunca supera al óptimo exacto
        if abs(got - best) <= 1e-6:
            exact += 1
        elif got >= 0.95 * best:
            close += 1
    assert exact >= 9, f"solo {exact}/10 coinciden con la fuerza bruta"
    assert exact + close == 10


def _hv(objs: np.ndarray, ref: np.ndarray) -> float:
    return float(HV(ref_point=ref)(objs)) if len(objs) else 0.0


@pytest.mark.slow
@pytest.mark.parametrize("seed", range(5))
def test_hypervolume_not_worse_than_greedy_with_15_pois(seed):
    plan = run(seed=seed, n=15, budget=BUDGET)
    ga = np.array([m.metrics.objectives() for m in plan.front])
    greedy = greedy_missions(plan.lm, plan.pois, CFG, BUDGET, MAX_TIME)
    gr = np.array([m.objectives() for _, m in greedy]) if greedy else np.empty((0, 3))
    both = np.vstack([ga, gr]) if len(gr) else ga
    ref = both.max(axis=0) + 1.0
    assert _hv(ga, ref) >= _hv(gr, ref) - 1e-9


@pytest.mark.slow
def test_15_pois_on_300x300_under_20s():
    bbox = (77.0, 18.0, 78.0, 18.9)  # ≈ 300×270 celdas a 200 m
    z, t, h, w = generate_dem(bbox, seed=1)
    assert h * w > 70_000
    grid = grid_from_dem(z, t)
    pois = make_pois(grid, 15, seed=0, bbox=bbox)
    t0 = time.perf_counter()
    plan = plan_missions(
        grid, (18.45, 77.5), pois, [], CFG, energy_budget_wh=12000.0, max_time_h=720.0,
        max_radius_m=40000.0, seed=1,
    )  # fmt: skip
    assert time.perf_counter() - t0 < 20.0
    assert len(plan.front) >= 1


def test_grid_fixture_sane():
    assert grid_for(1).shape[0] > 100 and HABITAT[0] > 18
