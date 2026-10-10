import time

import pytest

from marsmap.planning.astar import SearchTimeout
from marsmap.planning.presets import PRESETS
from marsmap.planning.service import RouteResult

ROUTE = "/api/regions/jezero/route"
FIELDS = {"status", "reason", "geometry", "distance_m", "straight_line_m", "tortuosity", "max_slope_deg",
          "mean_slope_deg", "elevation_gain_m", "elevation_loss_m", "pct_risk_cells", "est_time_h",
          "profile", "explanations", "weights_used", "compute_ms"}  # fmt: skip


def _pair(client, pts, preset="safe"):
    """Primer par de puntos que tiene ruta."""
    for a in pts[:12]:
        for b in pts[-12:]:
            r = client.post(ROUTE, json={"start": a, "goal": b, "preset": preset})
            if r.status_code == 200 and r.json()["status"] == "ok":
                return a, b, r
    pytest.skip("no se encontró un par conectado en el terreno sintético")


def test_presets_endpoint(client):
    r = client.get(f"{ROUTE}/presets")
    assert {p["preset"] for p in r.json()} == set(PRESETS)


def test_route_returns_all_fields(client, free_points):
    _, _, r = _pair(client, free_points)
    body = r.json()
    assert set(body) == FIELDS
    assert body["geometry"]["type"] == "LineString" and len(body["geometry"]["coordinates"]) > 2
    assert all(
        -180 <= lon <= 180 and -90 <= lat <= 90 for lon, lat in body["geometry"]["coordinates"]
    )
    assert body["tortuosity"] == pytest.approx(body["distance_m"] / body["straight_line_m"])
    assert 1 <= len(body["profile"]) <= 500
    assert len(body["explanations"]) >= 1 and body["max_slope_deg"] <= 15.0 + 1e-6


def test_fast_is_not_longer_than_safe_on_same_pair(client, free_points):
    a, b, safe = _pair(client, free_points, "safe")
    fast = client.post(ROUTE, json={"start": a, "goal": b, "preset": "fast"}).json()
    assert fast["distance_m"] <= safe.json()["distance_m"] + 1e-6


def test_custom_weights_and_validation(client, free_points):
    a, b = free_points[0], free_points[1]
    ok = client.post(
        ROUTE,
        json={"start": a, "goal": b, "weights": {"slope": 1, "rough": 1, "risk": 1, "science": 0}},
    )
    assert ok.status_code == 200 and ok.json()["weights_used"]["slope"] == 1
    bad = [
        {"start": a, "goal": b, "weights": {"slope": 11, "rough": 0, "risk": 0}},
        {"start": a, "goal": b, "weights": {"slope": -1, "rough": 0, "risk": 0}},
        {"start": a, "goal": b, "preset": "turbo"},
        {"start": a, "goal": b, "habitat": a, "max_radius_m": -5},
        {"start": a, "goal": b, "max_radius_m": 1000},  # radio sin hábitat
        {"start": {"lat": 100, "lon": 77}, "goal": b},
        {"start": a},
    ]
    for body in bad:
        r = client.post(ROUTE, json=body)
        assert r.status_code == 422 and r.json()["code"] == "validation_error", body


def test_blocked_start_and_goal_and_out_of_region(client, free_points, blocked_point):
    free = free_points[0]
    r = client.post(ROUTE, json={"start": blocked_point, "goal": free, "preset": "fast"})
    assert r.status_code == 422 and r.json()["code"] == "start_blocked"
    r = client.post(ROUTE, json={"start": free, "goal": blocked_point, "preset": "fast"})
    assert r.status_code == 422 and r.json()["code"] == "goal_blocked"
    r = client.post(ROUTE, json={"start": {"lat": 50, "lon": 10}, "goal": free, "preset": "fast"})
    assert r.status_code == 422 and r.json()["code"] == "out_of_region"


def test_goal_outside_walkback_radius_is_goal_blocked(client, free_points):
    a = free_points[0]
    far = max(free_points, key=lambda p: abs(p["lat"] - a["lat"]) + abs(p["lon"] - a["lon"]))
    r = client.post(
        ROUTE, json={"start": a, "goal": far, "habitat": a, "max_radius_m": 300, "preset": "fast"}
    )
    assert r.status_code == 422 and r.json()["code"] == "goal_blocked"


def test_no_route_is_200(client, free_points, monkeypatch):
    from marsmap.api.routers import routes

    monkeypatch.setattr(
        routes, "plan_route", lambda *a, **k: RouteResult("no_route", "aislado", PRESETS["fast"])
    )
    r = client.post(ROUTE, json={"start": free_points[0], "goal": free_points[1], "preset": "fast"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "no_route" and body["reason"] == "aislado" and body["geometry"] is None


def test_search_timeout_is_controlled_504(client, free_points, monkeypatch):
    from marsmap.api.routers import routes

    def slow(*a, **k):
        raise SearchTimeout("lento")

    monkeypatch.setattr(routes, "plan_route", slow)
    r = client.post(ROUTE, json={"start": free_points[0], "goal": free_points[1], "preset": "fast"})
    assert r.status_code == 504 and r.json()["code"] == "timeout"


def test_costmap_cache_is_reused(client, free_points):
    body = {"start": free_points[0], "goal": free_points[1], "preset": "balanced"}
    client.post(ROUTE, json=body)
    n = len(client.app.state.costmaps)
    client.post(ROUTE, json=body)
    assert len(client.app.state.costmaps) == n


@pytest.mark.slow
def test_route_on_full_jezero_grid_under_2s(client, free_points):
    a, b, _ = _pair(client, free_points, "balanced")
    t0 = time.perf_counter()
    r = client.post(ROUTE, json={"start": a, "goal": b, "preset": "balanced"})
    assert r.status_code == 200 and time.perf_counter() - t0 < 2.0
