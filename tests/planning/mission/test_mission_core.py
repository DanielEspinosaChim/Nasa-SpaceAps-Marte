import re

import numpy as np
import pytest

from marsmap.geo.coords import M_PER_DEG
from marsmap.planning.astar import astar
from marsmap.planning.mission.encoding import decode, encode, tour_time, two_opt
from marsmap.planning.mission.legs import build_leg_matrix
from marsmap.planning.mission.poi import pois_from_dicts
from marsmap.planning.mission.prefilter import prefilter
from marsmap.planning.presets import PRESETS
from marsmap.planning.service import build_constrained_costmap
from tests.planning.mission.helpers import BB, CFG, HABITAT, circle_zone, grid_for, make_pois


def test_leg_costs_match_astar_on_10_random_pairs():
    grid = grid_for(1)
    cm = build_constrained_costmap(grid, PRESETS["balanced"])
    pois = make_pois(grid, 6, seed=3)
    rcs = [grid.to_rowcol(*HABITAT), *(grid.to_rowcol(p.lat, p.lon) for p in pois)]
    lm = build_leg_matrix(cm, rcs, CFG.energy)
    assert lm.cost.shape == (7, 7)
    rng = np.random.default_rng(0)
    checked = 0
    while checked < 10:
        i, j = rng.choice(7, 2, replace=False)
        ref = astar(cm, rcs[i], rcs[j])
        if ref is None:
            assert not lm.reachable[i, j]
            continue
        assert lm.cost[i, j] == pytest.approx(ref.cost, abs=1e-6)
        assert lm.distance_m[i, j] > 0 and lm.energy_wh[i, j] > 0 and lm.time_h[i, j] > 0
        checked += 1


def test_decode_known_keys_and_empty_mission():
    assert decode(np.array([0.9, 0.2, 0.7, 0.6])) == (1, 3, 4)
    assert decode(np.array([0.1, 0.49, 0.0])) == ()


def test_encode_decode_roundtrip():
    rng = np.random.default_rng(0)
    for seq in [(), (3,), (2, 5, 1), (4, 1, 3, 2)]:
        assert decode(encode(seq, 6, rng)) == seq


def test_two_opt_never_worsens():
    rng = np.random.default_rng(1)
    for _ in range(30):
        n = int(rng.integers(3, 9))
        t = rng.uniform(1, 10, (n + 1, n + 1)).tolist()
        seq = tuple(rng.permutation(np.arange(1, n + 1)).tolist())
        assert tour_time(two_opt(seq, t), t) <= tour_time(seq, t) + 1e-12


def _local_offset(lat, lon, east_m):
    return lat, lon + east_m / (M_PER_DEG * np.cos(np.radians(lat)))


def test_prefilter_walkback_and_forbidden_zone():
    grid = grid_for(1)
    lat, lon = HABITAT
    far = _local_offset(lat, lon, 10_500)
    near = _local_offset(lat, lon, -3_000)
    zlat, zlon = _local_offset(lat, lon, -3_000)
    base = {"science_value": 0.5, "dwell_time_h": 1.0}
    pois = pois_from_dicts(
        [
            {**base, "poi_id": "lejos", "name": "Lejos", "lat": far[0], "lon": far[1]},
            {**base, "poi_id": "cerca", "name": "Cerca", "lat": near[0] + 0.05, "lon": near[1]},
            {**base, "poi_id": "zona", "name": "Zona", "lat": zlat, "lon": zlon},
        ]
    )
    zones = [circle_zone(zlat, zlon, 300.0, 50.0, name="RSL")]
    kept, disc = prefilter(pois, grid, zones, HABITAT, 10_000.0)
    codes = {d.poi_id: d.reason_code for d in disc}
    assert codes == {"lejos": "outside_walkback", "zona": "forbidden_zone"}
    assert [p.poi_id for p in kept] == ["cerca"]
    assert all(re.search(r"\d|RSL", d.reason) for d in disc)


def test_bbox_constant_is_jezero_like():
    assert BB[0] < HABITAT[1] < BB[2] and BB[1] < HABITAT[0] < BB[3]
