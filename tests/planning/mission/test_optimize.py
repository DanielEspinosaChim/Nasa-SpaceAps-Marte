import re

import numpy as np
import pytest

from marsmap.planning.mission.optimize import dominates
from marsmap.planning.mission.select import name_missions, select_mission
from marsmap.planning.service import RouteError
from tests.planning.mission.helpers import (
    CFG,
    HABITAT,
    circle_zone,
    forbidden_and_outside,
    grid_for,
    make_pois,
    run,
)


@pytest.mark.parametrize("seed", range(10))
def test_hard_constraints_never_violated(seed):
    grid = grid_for(1)
    zone = circle_zone(18.25, 77.25, 900.0, 100.0)
    budget, max_time, radius = 7000.0, 180.0, 9000.0
    plan = run(
        seed=seed,
        n=8,
        zones=[zone],
        budget=budget,
        max_time=max_time,
        radius=radius,
        pop_size=40,
        n_generations=40,
    )
    forb, outside = forbidden_and_outside(plan, [zone], radius=radius)
    for m in plan.front:
        assert m.metrics.energy_wh <= budget + 1e-6 and m.metrics.time_h <= max_time + 1e-6
        nodes = (0, *m.sequence, 0)
        assert nodes[0] == 0 and nodes[-1] == 0
        for a, b in zip(nodes[:-1], nodes[1:], strict=True):
            for r, c in plan.lm.paths[(a, b)]:
                assert grid.traversability[r, c] != 2 and not forb[r, c] and not outside[r, c]


def test_front_is_non_dominated_unique_and_bounded():
    plan = run(seed=2, n=10)
    assert 1 <= len(plan.front) <= CFG.ga.max_front_size
    seqs = [m.sequence for m in plan.front]
    assert len(seqs) == len(set(seqs))
    keys = [tuple(round(v, 6) for v in m.metrics.objectives()) for m in plan.front]
    assert len(keys) == len(set(keys))  # sin misiones con cifras idénticas
    objs = [m.metrics.objectives() for m in plan.front]
    for i, a in enumerate(objs):
        assert not any(dominates(b, a) for j, b in enumerate(objs) if j != i)


def test_named_missions_are_the_right_extremes():
    plan = run(seed=4, n=12)
    f = {m.mission_id: m.metrics for m in plan.front}
    n = plan.named
    assert set(n) == {"safe", "fast", "science", "balanced"}
    assert f[n["science"]].science_total == pytest.approx(max(m.science_total for m in f.values()))
    assert f[n["fast"]].time_h == pytest.approx(min(m.time_h for m in f.values()))
    assert f[n["safe"]].risk_score == pytest.approx(min(m.risk_score for m in f.values()))
    assert all(plan.mission(i).sequence for i in n.values())


def test_single_mission_front_names_coincide():
    plan = run(seed=0, n=1)
    assert len(plan.front) == 1
    assert len(set(plan.named.values())) == 1


def test_selector_pure_weights_match_named_and_validates():
    plan = run(seed=5, n=12)
    n = plan.named
    assert (
        select_mission(plan.front, {"safety": 1, "science": 0, "speed": 0}).mission_id == n["safe"]
    )
    assert (
        select_mission(plan.front, {"safety": 0, "science": 1, "speed": 0}).mission_id
        == n["science"]
    )
    assert (
        select_mission(plan.front, {"safety": 0, "science": 0, "speed": 1}).mission_id == n["fast"]
    )
    mid = select_mission(plan.front, {"safety": 0.3, "science": 0.3, "speed": 0.3})
    assert mid in plan.front
    for bad in (
        {"safety": 0, "science": 0, "speed": 0},
        {"safety": 2, "science": 0, "speed": 0},
        {"safety": 1},
    ):
        with pytest.raises(ValueError):
            select_mission(plan.front, bad)
    assert name_missions(plan.front) == n


def test_selector_science_weight_is_monotone():
    plan = run(seed=5, n=12)
    sci = [
        select_mission(
            plan.front, {"safety": 0.5, "science": w, "speed": 0.5}
        ).metrics.science_total
        for w in (0.0, 0.25, 0.5, 0.75, 1.0)
    ]
    assert sci == sorted(sci)


def test_determinism_same_seed_same_front():
    a, b = run(seed=6, n=9), run(seed=6, n=9)
    assert [(m.sequence, m.metrics) for m in a.front] == [(m.sequence, m.metrics) for m in b.front]


def test_explanations_cover_every_visited_and_discarded_poi():
    plan = run(seed=7, n=10, budget=7000.0)
    assert len(plan.pois) + len(plan.discarded) >= 8
    for m in plan.front:
        text = plan.explanations[m.mission_id]
        assert len(text) >= len(plan.pois) + len(plan.discarded)
        assert all(re.search(r"\d", t) for t in text)
        for k, p in enumerate(plan.pois, start=1):
            prefix = "Visita " if k in m.sequence else "Descarta "
            assert any(t.startswith(prefix + p.name) for t in text)


def test_geometry_and_legs_are_consistent():
    plan = run(seed=1, n=6)
    m = plan.mission(plan.named["balanced"])
    coords = plan.geometry(m)
    assert coords[0] == coords[-1]  # empieza y termina en el hábitat
    assert all(-180 <= lon <= 180 and -90 <= lat <= 90 for lon, lat in coords)
    legs = plan.legs(m)
    assert len(legs) == len(m.sequence) + 1
    assert sum(leg["energy_wh"] for leg in legs) <= m.metrics.energy_wh


def test_tiny_budget_gives_empty_mission_with_explanation():
    plan = run(seed=1, n=5, budget=50.0)
    assert len(plan.front) == 1 and plan.front[0].sequence == ()
    assert "vacía" in plan.explanations[plan.front[0].mission_id][0]
    empty = plan.front[0]
    assert plan.legs(empty) == []
    coords = plan.geometry(empty)  # no debe fallar: el rover permanece en el hábitat
    assert len(coords) == 2 and coords[0] == coords[1]


def test_habitat_errors():
    grid = grid_for(1)
    from marsmap.planning.mission.service import plan_missions

    pois = make_pois(grid, 3, 0)
    with pytest.raises(RouteError) as e:
        plan_missions(grid, (50.0, 10.0), pois, [], CFG)
    assert e.value.code == "out_of_region"
    blocked = np.argwhere(grid.traversability == 2)[0]
    lon, lat = grid.to_lonlat(*blocked)
    with pytest.raises(RouteError) as e:
        plan_missions(grid, (lat, lon), pois, [], CFG, max_radius_m=60000.0)
    assert e.value.code == "habitat_blocked"
    assert np.isfinite(HABITAT[0])


def test_no_pois_returns_empty_mission():
    grid = grid_for(1)
    from marsmap.planning.mission.service import plan_missions

    plan = plan_missions(grid, HABITAT, [], [], CFG, max_radius_m=20000.0)
    assert len(plan.front) == 1 and plan.front[0].sequence == ()
