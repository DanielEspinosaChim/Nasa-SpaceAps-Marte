"""Pruebas con el DEM REAL de NASA (MOLA–HRSC 200 m, recorte de Jezero).

Requieren `data/raw/jezero/dem.tif` (ver data/README.md); si falta, se omiten.
"""

from pathlib import Path

import numpy as np
import pytest

from marsmap.geo.coords import great_circle_m
from marsmap.planning.astar import astar
from marsmap.planning.constraints import load_forbidden_zones
from marsmap.planning.costmap import build_costmap
from marsmap.planning.dijkstra import dijkstra
from marsmap.planning.mission.baselines.bruteforce import best_science
from marsmap.planning.mission.config import load_config
from marsmap.planning.mission.poi import load_pois
from marsmap.planning.mission.service import plan_missions
from marsmap.planning.presets import PRESETS
from marsmap.planning.service import plan_route
from marsmap.planning.terrain_grid import load_grid
from marsmap.terrain.build import build
from marsmap.terrain.metadata import read_metadata

ROOT = Path(__file__).resolve().parents[2]
DEM = ROOT / "data" / "raw" / "jezero" / "dem.tif"
DATA = ROOT / "data" / "processed" / "jezero"
# Aterrizaje publicado por NASA (primer waypoint, sol 13), guardado junto a los POI reales.
_POI_FILE = ROOT / "data" / "processed" / "jezero" / "poi.geojson"
LANDING = (18.44462715, 77.45088572)
WALKBACK_M = 10_000.0

pytestmark = [
    pytest.mark.real,
    pytest.mark.skipif(not DEM.is_file(), reason="falta data/raw/jezero/dem.tif"),
]


@pytest.fixture(scope="module")
def grid(tmp_path_factory):
    out = build("jezero", tmp_path_factory.mktemp("real"), source=str(DEM))
    return load_grid(out), out


@pytest.fixture(scope="module")
def g(grid):
    return grid[0]


@pytest.fixture(scope="module")
def habitat(g):
    lat, lon = g.cell_centers()
    d = np.hypot(lat - LANDING[0], lon - LANDING[1]) + np.where(g.traversability == 0, 0, 1e3)
    r, c = np.unravel_index(np.argmin(d), d.shape)
    return float(lat[r, c]), float(lon[r, c])


def test_metadata_declares_the_real_source(grid):
    meta = read_metadata(grid[1])
    for layer in meta.layers:
        assert layer.source_dataset == "MOLA_HRSC_Blend_200m_v2"
        assert layer.instrument == "MGS MOLA + MEX HRSC"
        assert layer.resolution_m == pytest.approx(200.0, rel=0.02)
        assert -180 <= layer.bbox[0] < layer.bbox[2] <= 180
        assert layer.bbox[0] == pytest.approx(77.0) and layer.bbox[3] == pytest.approx(18.9)


def test_terrain_is_physically_plausible(g):
    e = g.elevation
    assert np.isfinite(e).all()
    assert -3500 < np.nanmin(e) < np.nanmax(e) < -500  # fondo de cráter, bajo el datum de Marte
    trav = g.traversability
    assert (trav == 0).mean() > 0.85  # el fondo de Jezero es mayormente llano
    assert 0.0 < (trav == 2).mean() < 0.10  # pero existen paredes bloqueadas
    assert np.nanmedian(g.slope) < 5


def test_landing_site_is_flat_and_low(g):
    r, c = g.to_rowcol(*LANDING)
    assert -3000 < g.elevation[r, c] < -2200
    assert g.slope[r, c] < 10 and g.traversability[r, c] == 0


def test_astar_matches_dijkstra_on_real_terrain(g):
    cm = build_costmap(g, PRESETS["balanced"])
    rr, cc = np.nonzero(~cm.blocked)
    free = list(zip(rr.tolist(), cc.tolist(), strict=True))
    rng = np.random.default_rng(3)
    for _ in range(10):
        a, b = (free[i] for i in rng.choice(len(free), 2, replace=False))
        ra, rd = astar(cm, a, b), dijkstra(cm, a, b)
        assert (ra is None) == (rd is None)
        if ra:
            assert ra.cost == pytest.approx(rd.cost, abs=1e-6)
            assert not any(cm.blocked[r, c] for r, c in ra.cells)


def test_routes_to_real_poi_safe_vs_fast(g, habitat):
    pois = load_pois(DATA / "poi.geojson")
    delta = next(p for p in pois if p.poi_id == "s16_kukaklek")  # Fan Front, ~3 km
    res = {
        name: plan_route(g, habitat, (delta.lat, delta.lon), PRESETS[name])
        for name in ("safe", "fast")
    }
    assert all(r.status == "ok" for r in res.values())
    for r in res.values():
        assert r.metrics.max_slope_deg <= 15 and r.explanations
    assert res["fast"].metrics.distance_m <= res["safe"].metrics.distance_m + 1e-6
    assert res["safe"].metrics.pct_risk_cells <= res["fast"].metrics.pct_risk_cells + 1e-9


@pytest.fixture(scope="module")
def plan(g, habitat):
    cfg = load_config()
    pois = load_pois(DATA / "poi.geojson")
    zones = load_forbidden_zones(DATA / "forbidden_zones.geojson")
    return plan_missions(g, habitat, pois, zones, cfg, seed=7), cfg, habitat


def test_missions_respect_all_hard_constraints(plan, g):
    p, cfg, habitat = plan
    assert len(p.front) >= 3
    lat, lon = g.cell_centers()
    outside = great_circle_m(habitat[0], habitat[1], lat, lon) > p.max_radius_m
    for m in p.front:
        assert m.metrics.energy_wh <= p.energy_budget_wh + 1e-6
        assert m.metrics.time_h <= p.max_time_h + 1e-6
        nodes = (0, *m.sequence, 0)
        for a, b in zip(nodes[:-1], nodes[1:], strict=True):
            for r, c in p.lm.paths[(a, b)]:
                assert g.traversability[r, c] != 2 and not outside[r, c]


def test_far_pois_are_discarded_by_walkback(plan):
    p, _, habitat = plan
    pois = load_pois(DATA / "poi.geojson")
    far = {
        q.poi_id for q in pois if great_circle_m(habitat[0], habitat[1], q.lat, q.lon) > WALKBACK_M
    }
    assert far  # el borde del cráter (Witch Hazel Hill) está a ~10.5 km del aterrizaje
    codes = {d.poi_id: d.reason_code for d in p.discarded}
    assert far <= set(codes) and all(codes[i] == "outside_walkback" for i in far)
    assert not far & {q.poi_id for q in p.pois}


def test_genetic_matches_bruteforce_on_real_terrain(g, habitat):
    """Con 8 sitios reales de muestras, el genético iguala a probar todos los órdenes."""
    cfg = load_config()
    pois = load_pois(DATA / "poi.geojson")
    inside = [q for q in pois if great_circle_m(habitat[0], habitat[1], q.lat, q.lon) <= WALKBACK_M]
    subset = inside[1::2][:8]  # 8 sitios repartidos por todo el recorrido
    assert len(subset) == 8
    for budget in (6000.0, 9000.0):
        p = plan_missions(g, habitat, subset, [], cfg, energy_budget_wh=budget, seed=7)
        _, best = best_science(p.lm, p.pois, cfg, budget, p.max_time_h)
        got = p.mission(p.named["science"]).metrics.science_total
        assert got == pytest.approx(best, abs=1e-6)


def test_pois_are_real_nasa_sample_sites():
    import json

    data = json.loads(_POI_FILE.read_text(encoding="utf-8"))
    assert "Mars 2020" in data["source"] and data["landing_site"]["lat"] == LANDING[0]
    pois = load_pois(_POI_FILE)
    assert len(pois) >= 20
    assert all(p.source.startswith("NASA/JPL Mars 2020") for p in pois)
    assert {"s2_3_montdenier_montagnac", "s24_comet_geyser", "s25_sapphire_canyon"} <= {
        p.poi_id for p in pois
    }
    # Todo sitio cae en la región cartografiada.
    assert all(77.0 <= p.lon <= 78.0 and 18.0 <= p.lat <= 18.9 for p in pois)


def test_front_trades_science_for_time(plan):
    p, *_ = plan
    sci = p.mission(p.named["science"]).metrics
    fast = p.mission(p.named["fast"]).metrics
    assert sci.science_total > fast.science_total and sci.time_h > fast.time_h
    assert all(p.explanations[m.mission_id] for m in p.front)
