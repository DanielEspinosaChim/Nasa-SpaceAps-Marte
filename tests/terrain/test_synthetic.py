import numpy as np

from marsmap.terrain.synthetic import generate_dem, generate_pois

BBOX = (77.0, 18.0, 78.0, 18.9)


def test_synthetic_is_deterministic():
    a, ta, *_ = generate_dem(BBOX, seed=7)
    b, tb, *_ = generate_dem(BBOX, seed=7)
    assert ta == tb
    assert a.tobytes() == b.tobytes()


def test_different_seeds_differ():
    a, *_ = generate_dem(BBOX, seed=1)
    b, *_ = generate_dem(BBOX, seed=2)
    assert not np.array_equal(a, b)


def test_synthetic_shape_and_values():
    z, t, h, w = generate_dem(BBOX)
    assert z.shape == (h, w) and 250 < w < 320 and 240 < h < 300
    assert np.isfinite(z).all()
    assert -4000 < z.min() < z.max() < 0


def test_synthetic_pois_deterministic_and_inside():
    p1 = generate_pois(BBOX, 10, seed=3)
    assert p1 == generate_pois(BBOX, 10, seed=3)
    for p in p1:
        assert BBOX[0] < p["lon"] < BBOX[2] and BBOX[1] < p["lat"] < BBOX[3]
        assert 0 <= p["science_value"] <= 1
