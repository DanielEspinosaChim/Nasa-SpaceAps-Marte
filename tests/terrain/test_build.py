import json
import time

import numpy as np
import pytest
import rasterio

from marsmap.terrain import build as build_mod
from marsmap.terrain.metadata import RegionMetadata
from marsmap.terrain.synthetic import generate_dem

FILES = ["elevation.tif", "slope.tif", "roughness.tif", "hillshade.tif", "traversability.tif"]


def test_cli_synthetic_generates_aligned_layers(tmp_path):
    args = ["--region", "jezero", "--synthetic", "--seed", "42", "--out", str(tmp_path)]
    assert build_mod.main(args) == 0
    folder = tmp_path / "jezero"
    sigs = set()
    for f in FILES:
        with rasterio.open(folder / f) as ds:
            sigs.add((ds.width, ds.height, tuple(ds.transform), ds.crs.to_string()))
    assert len(sigs) == 1
    meta = RegionMetadata.model_validate_json(
        (folder / "metadata.json").read_text(encoding="utf-8")
    )
    assert {layer.layer_id for layer in meta.layers} == {f[:-4] for f in FILES}
    for layer in meta.layers:
        assert -180 <= layer.bbox[0] < layer.bbox[2] <= 180
        assert layer.limitations and layer.source_dataset.startswith("synthetic")


def test_synthetic_build_is_byte_identical(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1791504000")
    for d in ("a", "b"):
        build_mod.build("jezero", tmp_path / d, synthetic=True, seed=5)
    for f in [*FILES, "metadata.json"]:
        assert (tmp_path / "a/jezero" / f).read_bytes() == (tmp_path / "b/jezero" / f).read_bytes()


@pytest.mark.parametrize(
    "bbox", [["77", "19", "78", "18"], ["77", "18", "78", "95"], ["10", "10", "10", "11"]]
)
def test_invalid_bbox_exits_nonzero_without_partial_files(tmp_path, bbox):
    args = ["--region", "jezero", "--synthetic", "--out", str(tmp_path), "--bbox", *bbox]
    assert build_mod.main(args) != 0
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("region", ["../etc", "JEZERO", "jezero/../x", "no_existe"])
def test_invalid_region_rejected(tmp_path, region):
    assert build_mod.main(["--region", region, "--synthetic", "--out", str(tmp_path)]) != 0
    assert list(tmp_path.iterdir()) == []


def _write_fake_dem(path, bbox=(76.5, 17.5, 78.5, 19.5)):
    z, t, h, w = generate_dem(bbox, seed=1)
    z[0:5, 0:5] = -32768
    with rasterio.open(
        path, "w", driver="GTiff", height=h, width=w, count=1, dtype="float32",
        crs="+proj=longlat +R=3396190 +no_defs", transform=t, nodata=-32768,
    ) as dst:  # fmt: skip
        dst.write(z, 1)


def test_build_from_real_like_dem(tmp_path):
    dem = tmp_path / "dem.tif"
    _write_fake_dem(dem)
    out = build_mod.build("jezero", tmp_path / "out", source=str(dem))
    with rasterio.open(out / "slope.tif") as ds:
        assert np.isfinite(ds.read(1)).mean() > 0.99
    meta = json.loads((out / "metadata.json").read_text(encoding="utf-8"))
    assert meta["layers"][0]["source_dataset"] == "MOLA_HRSC_Blend_200m_v2"


def test_build_from_projected_dem(tmp_path):
    """El DEM MOLA–HRSC real viene en equirectangular (metros); se reproyecta a lon/lat."""
    from rasterio.warp import calculate_default_transform, reproject

    geo = tmp_path / "geo.tif"
    _write_fake_dem(geo)
    eqc = "+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R=3396190 +units=m +no_defs"
    dem = tmp_path / "eqc.tif"
    with rasterio.open(geo) as src:
        t, w, h = calculate_default_transform(src.crs, eqc, src.width, src.height, *src.bounds)
        prof = src.profile | {"crs": eqc, "transform": t, "width": w, "height": h}
        with rasterio.open(dem, "w", **prof) as dst:
            reproject(rasterio.band(src, 1), rasterio.band(dst, 1))
    out = build_mod.build("jezero", tmp_path / "out", source=str(dem))
    meta = json.loads((out / "metadata.json").read_text(encoding="utf-8"))
    assert 150 < meta["layers"][0]["resolution_m"] < 250


def test_bbox_outside_dem_coverage_fails_cleanly(tmp_path):
    dem = tmp_path / "dem.tif"
    _write_fake_dem(dem, bbox=(10.0, 10.0, 11.0, 11.0))
    out = tmp_path / "out"
    with pytest.raises(build_mod.BuildError, match="cobertura"):
        build_mod.build("jezero", out, source=str(dem))
    assert not (out / "jezero").exists()


def test_rebuild_keeps_geojson_files(tmp_path):
    build_mod.build("jezero", tmp_path, synthetic=True)
    (tmp_path / "jezero/poi.geojson").write_text("{}", encoding="utf-8")
    build_mod.build("jezero", tmp_path, synthetic=True, seed=9)
    assert (tmp_path / "jezero/poi.geojson").exists()


def test_synthetic_terrain_has_all_traversability_classes(tmp_path):
    out = build_mod.build("jezero", tmp_path, synthetic=True)
    with rasterio.open(out / "traversability.tif") as ds:
        values = set(np.unique(ds.read(1)).tolist())
    assert {0, 1, 2} <= values


@pytest.mark.slow
def test_build_performance(tmp_path):
    t0 = time.perf_counter()
    build_mod.build("jezero", tmp_path, synthetic=True)
    assert time.perf_counter() - t0 < 30
