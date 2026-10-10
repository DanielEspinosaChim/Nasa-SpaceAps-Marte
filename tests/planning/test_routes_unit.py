import re

import numpy as np
import pytest
from shapely.geometry import Point

from marsmap.geo.coords import great_circle_m
from marsmap.planning.constraints import forbidden_mask
from marsmap.planning.metrics import compute_metrics
from marsmap.planning.presets import PRESETS
from marsmap.planning.service import RouteError, plan_route
from tests.planning.helpers import ZERO_WEIGHTS, costmap, flat_grid, free_cells, random_grid


def _pt(grid, rc):
    lon, lat = grid.to_lonlat(*rc)
    return lat, lon


def _circle_zone(lat, lon, radius_m, buffer_m):
    from marsmap.geo.coords import M_PER_DEG

    kx = M_PER_DEG * np.cos(np.radians(lat))
    t = np.linspace(0, 2 * np.pi, 361)
    ring = [(lon + radius_m * np.cos(a) / kx, lat + radius_m * np.sin(a) / M_PER_DEG) for a in t]
    from shapely.geometry import Polygon

    return {"name": "rsl", "buffer_m": buffer_m, "geometry": Polygon(ring)}


def test_forbidden_zone_buffer_blocks_cell_10m_from_border():
    grid = flat_grid(30, 30)
    lon_c, lat_c = grid.to_lonlat(15, 15)
    lon_t, lat_t = grid.to_lonlat(15, 17)  # celda objetivo, 2 columnas al Este
    d = float(great_circle_m(lat_c, lon_c, lat_t, lon_t))
    radius = d - 10.0  # el borde queda 10 m antes de la celda
    with_buffer = forbidden_mask(grid, [_circle_zone(lat_c, lon_c, radius, 50.0)])
    without = forbidden_mask(grid, [_circle_zone(lat_c, lon_c, radius, 0.0)])
    assert with_buffer[15, 17] and not without[15, 17]
    assert with_buffer.sum() > without.sum()


def test_hard_constraints_zero_violations_in_100_random_routes():
    grid = random_grid(60, 60, seed=11)
    zone_poly = Point(*grid.to_lonlat(30, 30)).buffer(0.03)
    zones = [{"name": "z", "buffer_m": 100.0, "geometry": zone_poly}]
    habitat = _pt(grid, (30, 10))
    radius = 4000.0
    cm0 = costmap(grid, "balanced")
    from marsmap.planning.service import build_constrained_costmap

    cm = build_constrained_costmap(grid, PRESETS["balanced"], zones, habitat, radius)
    free = free_cells(cm)
    assert cm.blocked.sum() > cm0.blocked.sum()
    forb = forbidden_mask(grid, zones)
    lat_g, lon_g = grid.cell_centers()
    outside = great_circle_m(habitat[0], habitat[1], lat_g, lon_g) > radius
    rng = np.random.default_rng(0)
    checked = 0
    for _ in range(100):
        a, b = (free[i] for i in rng.choice(len(free), 2, replace=False))
        res = plan_route(grid, _pt(grid, a), _pt(grid, b), PRESETS["balanced"], costmap=cm)
        if res.status != "ok":
            continue
        checked += 1
        for r, c in res.cells:
            assert grid.traversability[r, c] != 2 and not forb[r, c] and not outside[r, c]
    assert checked >= 60


def test_blocked_start_and_out_of_region_error_codes():
    grid = random_grid(50, 50, seed=2)
    cm = costmap(grid, "balanced")
    blocked = np.argwhere(cm.blocked)[0]
    free = free_cells(cm)[0]
    with pytest.raises(RouteError) as e:
        plan_route(grid, _pt(grid, tuple(blocked)), _pt(grid, free), PRESETS["fast"])
    assert e.value.code == "start_blocked"
    with pytest.raises(RouteError) as e:
        plan_route(grid, _pt(grid, free), _pt(grid, tuple(blocked)), PRESETS["fast"])
    assert e.value.code == "goal_blocked"
    with pytest.raises(RouteError) as e:
        plan_route(grid, (50.0, 10.0), _pt(grid, free), PRESETS["fast"])
    assert e.value.code == "out_of_region"


def test_isolated_goal_returns_no_route():
    grid = flat_grid(30, 30)
    cm = costmap(grid, ZERO_WEIGHTS)
    cm.blocked[10:13, 10:13] = True
    cm.blocked[11, 11] = False  # celda aislada rodeada de bloqueo
    cm.mult[cm.blocked] = np.inf
    res = plan_route(grid, _pt(grid, (2, 2)), _pt(grid, (11, 11)), ZERO_WEIGHTS, costmap=cm)
    assert res.status == "no_route" and res.reason


def test_metrics_on_flat_plane_straight_line():
    grid = flat_grid(40, 40)
    cm = costmap(grid, "fast")
    res = plan_route(grid, _pt(grid, (20, 2)), _pt(grid, (20, 37)), PRESETS["fast"], costmap=cm)
    m = res.metrics
    assert m.tortuosity == pytest.approx(1.0, abs=0.05)
    assert m.max_slope_deg < 1 and m.elevation_gain_m == pytest.approx(0, abs=1e-6)
    assert m.est_time_h == pytest.approx(m.distance_m / 100.0)
    assert 1 <= len(m.profile) <= 500 and m.profile[0]["d_m"] == 0
    assert all(p["risk"] is False for p in m.profile)  # terreno plano: sin riesgo


def test_profile_is_subsampled_to_500_points():
    grid = flat_grid(30, 700)
    cm = costmap(grid, "fast")
    res = plan_route(grid, _pt(grid, (15, 2)), _pt(grid, (15, 690)), PRESETS["fast"], costmap=cm)
    assert len(res.metrics.profile) <= 500
    assert res.metrics.profile[-1]["d_m"] == pytest.approx(res.metrics.distance_m)


def test_explanations_always_present_with_numbers():
    grid = random_grid(60, 60, seed=5)
    cm = costmap(grid, "safe")
    free = free_cells(cm)
    rng = np.random.default_rng(1)
    for _ in range(15):
        a, b = (free[i] for i in rng.choice(len(free), 2, replace=False))
        res = plan_route(grid, _pt(grid, a), _pt(grid, b), PRESETS["safe"], costmap=cm)
        if res.status == "ok":
            assert len(res.explanations) >= 1
            assert all(re.search(r"\d", t) for t in res.explanations)


def test_explanation_mentions_detour_when_straight_line_is_blocked():
    grid = flat_grid(40, 40)
    cm = costmap(grid, ZERO_WEIGHTS)
    cm.blocked[10:30, 20] = True
    cm.mult[cm.blocked] = np.inf
    res = plan_route(grid, _pt(grid, (20, 3)), _pt(grid, (20, 37)), ZERO_WEIGHTS, costmap=cm)
    assert any("bloqueadas" in t and "desvío" in t for t in res.explanations)


def test_presets_safe_is_gentler_and_fast_is_shorter():
    """Minimizar un costo ponderado no garantiza el orden en cada ruta: se mide en agregado."""
    grid = random_grid(60, 60, seed=21)
    cm_s, cm_f = costmap(grid, "safe"), costmap(grid, "fast")
    free = free_cells(cm_s)
    rng = np.random.default_rng(4)
    pairs = []
    for _ in range(30):
        a, b = (free[i] for i in rng.choice(len(free), 2, replace=False))
        s = plan_route(grid, _pt(grid, a), _pt(grid, b), PRESETS["safe"], costmap=cm_s)
        f = plan_route(grid, _pt(grid, a), _pt(grid, b), PRESETS["fast"], costmap=cm_f)
        if s.status == f.status == "ok":
            pairs.append((s.metrics, f.metrics))
    assert len(pairs) >= 15
    assert np.mean([s.max_slope_deg for s, _ in pairs]) <= np.mean(
        [f.max_slope_deg for _, f in pairs]
    )
    assert np.mean([f.distance_m for _, f in pairs]) <= np.mean([s.distance_m for s, _ in pairs])
    assert np.mean([f.distance_m <= s.distance_m + 1e-6 for s, f in pairs]) >= 0.8
    assert np.mean([s.max_slope_deg <= f.max_slope_deg + 1e-9 for s, f in pairs]) >= 0.8


def test_science_preset_prefers_route_near_poi():
    grid = flat_grid(40, 60)
    lat, lon = grid.to_lonlat(8, 30)[::-1]
    poi = {"lat": lat, "lon": lon, "science_value": 1.0}
    a, b = _pt(grid, (20, 2)), _pt(grid, (20, 57))
    r_sci = plan_route(grid, a, b, PRESETS["science"], pois=[poi])
    r_bal = plan_route(grid, a, b, PRESETS["balanced"], pois=[poi])
    top = lambda r: min(c[0] for c in r.cells)  # noqa: E731
    assert top(r_sci) <= top(r_bal)
    assert compute_metrics(r_sci.costmap, r_sci.cells).distance_m >= r_bal.metrics.distance_m - 1e-6
