import numpy as np
import pytest
from affine import Affine

from marsmap.geo.coords import M_PER_DEG, cell_size_m, row_latitudes
from marsmap.terrain import derive

DEG = 200.0 / M_PER_DEG


def _plane(theta_deg, lat0, shape=(40, 40), direction="ew"):
    """Plano con pendiente física θ sobre una malla lon/lat centrada en lat0."""
    h, w = shape
    t = Affine(DEG, 0, 77.0, 0, -DEG, lat0 + h * DEG / 2)
    lats = row_latitudes(t, h)
    dx, dy = cell_size_m(t, lats)
    g = np.tan(np.radians(theta_deg))
    if direction == "ew":
        z = g * (np.arange(w)[None, :] * dx[:, None])  # metros reales por fila
    else:
        z = g * (np.arange(h)[:, None] * dy) * np.ones((1, w))
    return z, dx, dy


@pytest.mark.parametrize("theta", [5.0, 12.0, 20.0])
@pytest.mark.parametrize("direction", ["ew", "ns"])
def test_slope_on_inclined_plane(theta, direction):
    z, dx, dy = _plane(theta, 18.4, direction=direction)
    s = derive.slope_deg(z, dx, dy)[1:-1, 1:-1]
    assert np.allclose(s, theta, atol=0.5)


def test_slope_same_physical_slope_at_lat_0_and_60():
    for theta in (5.0, 12.0):
        s0 = derive.slope_deg(*_plane(theta, 0.0))[1:-1, 1:-1]
        s60 = derive.slope_deg(*_plane(theta, 60.0))[1:-1, 1:-1]
        assert np.allclose(s0, theta, atol=0.5)
        assert np.allclose(s60, theta, atol=0.5)


@pytest.mark.parametrize(
    ("slope", "expected"),
    [(9.99, 0), (10.0, 1), (15.0, 1), (15.01, 2), (np.nan, 255)],
)
def test_traversability_thresholds(slope, expected):
    assert derive.traversability(np.array([[slope]]))[0, 0] == expected


def test_nodata_propagates_to_all_layers():
    z, dx, dy = _plane(8.0, 18.4)
    z[10, 10] = np.nan
    assert np.isnan(derive.slope_deg(z, dx, dy)[10, 10])
    assert np.isnan(derive.roughness(z)[10, 10])
    assert derive.hillshade(z, dx, dy)[10, 10] == derive.HILLSHADE_NODATA
    trav = derive.traversability(derive.slope_deg(z, dx, dy))
    assert trav[10, 10] == derive.TRAV_NODATA
    # Nunca se trata como seguro, ni la celda ni sus vecinos inmediatos.
    assert not (trav[9:12, 9:12] == derive.TRAV_SAFE).any()


def test_roughness_zero_on_flat_and_positive_on_bumps():
    flat = np.full((10, 10), -2500.0)
    assert np.allclose(derive.roughness(flat), 0.0, atol=1e-3)
    bumpy = flat.copy()
    bumpy[5, 5] += 30.0
    assert derive.roughness(bumpy)[5, 5] > 5.0


def test_hillshade_range():
    z, dx, dy = _plane(12.0, 18.4)
    hs = derive.hillshade(z, dx, dy)
    assert hs.dtype == np.uint8 and hs.min() >= 1
