import numpy as np
import pytest
from affine import Affine

from marsmap.config.regions import validate_bbox
from marsmap.geo.coords import M_PER_DEG, cell_size_m, normalize_lon


@pytest.mark.parametrize(
    ("lon", "expected"),
    [(282.5, -77.5), (77.5, 77.5), (180.0, 180.0), (-180.0, -180.0), (360.0, 0.0), (190.0, -170.0)],
)
def test_normalize_lon(lon, expected):
    assert normalize_lon(lon) == pytest.approx(expected)


def test_normalize_lon_is_idempotent():
    for lon in np.linspace(-180, 360, 97):
        once = normalize_lon(lon)
        assert normalize_lon(once) == once


def test_cell_size_corrects_by_latitude():
    t = Affine(0.01, 0, 0, 0, -0.01, 0)
    dx0, dy = cell_size_m(t, 0.0)
    dx60, _ = cell_size_m(t, 60.0)
    assert float(dx0) == pytest.approx(0.01 * M_PER_DEG)
    assert float(dx60) == pytest.approx(0.5 * float(dx0))
    assert dy == pytest.approx(0.01 * M_PER_DEG)


@pytest.mark.parametrize(
    "bbox",
    [[77, 19, 78, 18], [77, 18, 77, 19], [77, -95, 78, 18], [77, 18, 400, 19]],
)
def test_invalid_bbox_rejected(bbox):
    with pytest.raises(ValueError):
        validate_bbox(bbox)


def test_bbox_0_360_is_normalized():
    assert validate_bbox([282.0, 18.0, 283.0, 19.0]) == (-78.0, 18.0, -77.0, 19.0)


def test_lonlat_to_rowcol_corners_and_center():
    from marsmap.geo.coords import lonlat_to_rowcol, rowcol_to_lonlat

    t = Affine(0.01, 0, 77.0, 0, -0.01, 19.0)  # 100×100 celdas, fila 0 al Norte
    assert lonlat_to_rowcol(t, 77.001, 18.999) == (0, 0)  # esquina NO
    assert lonlat_to_rowcol(t, 77.999, 18.001) == (99, 99)  # esquina SE
    assert lonlat_to_rowcol(t, 77.5, 18.5) == (50, 50)  # centro
    for r, c in [(0, 0), (99, 99), (12, 80)]:
        lon, lat = rowcol_to_lonlat(t, r, c)
        assert lonlat_to_rowcol(t, lon, lat) == (r, c)
    # El 282.5 °E de entrada se normaliza antes de buscar la celda.
    t2 = Affine(0.01, 0, -78.0, 0, -0.01, 19.0)
    assert lonlat_to_rowcol(t2, 282.5, 18.5) == (50, 50)
