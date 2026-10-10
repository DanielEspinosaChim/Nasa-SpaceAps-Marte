import time

import numpy as np
import pytest

from marsmap.planning.astar import SearchTimeout, astar
from marsmap.planning.dijkstra import dijkstra
from marsmap.planning.graph import build_graph, multi_source, reconstruct
from tests.planning.helpers import ZERO_WEIGHTS, costmap, flat_grid, free_cells, random_grid


def test_wall_with_single_gap_forces_path_through_gap():
    grid = flat_grid(30, 30)
    cm = costmap(grid, ZERO_WEIGHTS)
    cm.blocked[:, 15] = True
    cm.blocked[22, 15] = False  # único hueco
    cm.mult[cm.blocked] = np.inf
    res = astar(cm, (5, 3), (5, 27))
    assert res is not None
    assert (22, 15) in res.cells
    assert not any(cm.blocked[r, c] for r, c in res.cells)


def test_no_route_when_fully_walled():
    cm = costmap(flat_grid(20, 20), ZERO_WEIGHTS)
    cm.blocked[:, 10] = True
    cm.mult[cm.blocked] = np.inf
    assert astar(cm, (5, 2), (5, 18)) is None


def test_start_equals_goal():
    cm = costmap(flat_grid(10, 10), ZERO_WEIGHTS)
    res = astar(cm, (3, 3), (3, 3))
    assert res.cells == [(3, 3)] and res.cost == 0.0


@pytest.mark.parametrize("seed", range(20))
def test_astar_matches_dijkstra_cost(seed):
    cm = costmap(random_grid(50, 50, seed), "balanced")
    free = free_cells(cm)
    rng = np.random.default_rng(seed)
    a, b = (free[i] for i in rng.choice(len(free), 2, replace=False))
    ra, rd = astar(cm, a, b), dijkstra(cm, a, b)
    assert (ra is None) == (rd is None)
    if ra is not None:
        assert ra.cost == pytest.approx(rd.cost, abs=1e-6)
        assert ra.expanded <= rd.expanded


@pytest.mark.parametrize("seed", range(5))
def test_sparse_graph_matches_astar(seed):
    cm = costmap(random_grid(40, 40, seed), "safe")
    free = free_cells(cm)
    rng = np.random.default_rng(100 + seed)
    w = cm.shape[1]
    ids = [free[i] for i in rng.choice(len(free), 4, replace=False)]
    src = [r * w + c for r, c in ids]
    dist, pred = multi_source(build_graph(cm), src)
    for i, s in enumerate(ids):
        for j, t in enumerate(ids):
            if i == j:
                continue
            ref = astar(cm, s, t)
            got = dist[i, src[j]]
            if ref is None:
                assert np.isinf(got)
            else:
                assert got == pytest.approx(ref.cost, abs=1e-6)
                path = reconstruct(pred[i], src[i], src[j], w)
                assert path[0] == s and path[-1] == t


def test_timeout_raises_controlled_error():
    cm = costmap(flat_grid(120, 120), ZERO_WEIGHTS)
    with pytest.raises(SearchTimeout):
        dijkstra(cm, (0, 0), (119, 119), timeout_s=1e-9)


@pytest.mark.slow
def test_300x300_under_2s():
    cm = costmap(random_grid(300, 300, 3), "balanced")
    free = free_cells(cm)
    a, b = free[0], free[-1]
    t0 = time.perf_counter()
    astar(cm, a, b)
    assert time.perf_counter() - t0 < 2.0
