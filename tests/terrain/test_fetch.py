import numpy as np
import pytest
import rasterio

from marsmap.terrain import build as build_mod
from marsmap.terrain.fetch import check_url, crop, main
from marsmap.terrain.synthetic import generate_dem


@pytest.mark.parametrize(
    "url",
    [
        "http://astrogeology.usgs.gov/x.tif",  # sin TLS
        "https://evil.example.com/x.tif",
        "https://usgs.gov.evil.com/x.tif",
        "https://notusgs.gov/x.tif",
        "file:///etc/passwd",
    ],
)
def test_url_whitelist_rejects(url):
    with pytest.raises(ValueError):
        check_url(url)


@pytest.mark.parametrize(
    "url", ["https://astrogeology.usgs.gov/a.tif", "https://pds.nasa.gov/a.tif"]
)
def test_url_whitelist_accepts(url):
    assert check_url(url) == url


def test_crop_local_dem_and_build(tmp_path):
    z, t, h, w = generate_dem((70.0, 10.0, 85.0, 25.0), resolution_m=2000.0, seed=1)
    big = tmp_path / "big.tif"
    with rasterio.open(
        big, "w", driver="GTiff", height=h, width=w, count=1, dtype="float32",
        crs="+proj=longlat +R=3396190 +no_defs", transform=t, nodata=-32768,
    ) as dst:  # fmt: skip
        dst.write(z, 1)
    out = tmp_path / "raw" / "jezero" / "dem.tif"
    assert main(["--region", "jezero", "--source", str(big), "--out", str(out)]) == 0
    with rasterio.open(out) as ds, rasterio.open(big) as src:
        assert ds.width < src.width and ds.height < src.height
        assert ds.bounds.left <= 77.0 and ds.bounds.right >= 78.0
    # El recorte alimenta el pipeline sin más pasos.
    folder = build_mod.build("jezero", tmp_path / "proc", source=str(out))
    assert (folder / "slope.tif").exists()


def test_crop_outside_coverage_fails(tmp_path):
    z, t, h, w = generate_dem((10.0, 10.0, 12.0, 12.0), resolution_m=2000.0)
    p = tmp_path / "far.tif"
    with rasterio.open(
        p, "w", driver="GTiff", height=h, width=w, count=1, dtype="float32",
        crs="+proj=longlat +R=3396190 +no_defs", transform=t,
    ) as dst:  # fmt: skip
        dst.write(z, 1)
    with pytest.raises(ValueError, match="cobertura"):
        crop(str(p), (77.0, 18.0, 78.0, 18.9), tmp_path / "o.tif")
    assert main(["--region", "jezero", "--url", "https://evil.example.com/a.tif"]) == 2
    assert np.isfinite(z).all()
