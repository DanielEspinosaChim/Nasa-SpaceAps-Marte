import io

import pytest
from PIL import Image

LAYERS = {"elevation", "slope", "roughness", "hillshade", "traversability"}


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_regions(client):
    regions = client.get("/api/regions").json()
    jez = next(r for r in regions if r["region_id"] == "jezero")
    assert jez["name"] and len(jez["bbox"]) == 4
    assert -180 <= jez["bbox"][0] < jez["bbox"][2] <= 180


def test_layers_have_metadata_and_legend(client):
    layers = client.get("/api/regions/jezero/layers").json()
    assert {layer["layer_id"] for layer in layers} == LAYERS
    for layer in layers:
        for k in ("name", "units", "source_dataset", "instrument", "resolution_m", "crs", "bbox",
                  "generated_at", "limitations", "legend", "image_url"):  # fmt: skip
            assert layer[k] not in (None, "", [])
        assert all(set(i) == {"value", "color", "label"} for i in layer["legend"])
        assert all(i["color"].startswith("#") and len(i["color"]) == 7 for i in layer["legend"])


@pytest.mark.parametrize("layer", sorted(LAYERS))
def test_layer_image_is_png_rgba(client, layer):
    r = client.get(f"/api/regions/jezero/layers/{layer}/image")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert "max-age" in r.headers["cache-control"]
    img = Image.open(io.BytesIO(r.content))
    assert img.mode == "RGBA" and img.size[0] > 100


def test_traversability_png_uses_legend_colors(client):
    img = Image.open(
        io.BytesIO(client.get("/api/regions/jezero/layers/traversability/image").content)
    )
    colors = {px[:3] for px in img.getdata()}
    assert {(0x3F, 0xA3, 0x4D), (0xD1, 0x49, 0x5B)} <= colors


def test_nodata_is_transparent(data_dir, tmp_path):
    import numpy as np
    import rasterio

    from marsmap.api import render

    src = data_dir / "jezero" / "slope.tif"
    out = tmp_path / "slope.tif"
    with rasterio.open(src) as ds:
        arr, prof = ds.read(1), ds.profile
    arr[:10, :10] = np.nan
    with rasterio.open(out, "w", **prof) as dst:
        dst.write(arr, 1)
    img = np.array(Image.open(io.BytesIO(render.render_png("slope", out))))
    assert (img[:10, :10, 3] == 0).all() and (img[20:30, 20:30, 3] > 0).all()


def test_cell_query(client, grid):
    lon, lat = grid.to_lonlat(grid.shape[0] // 2, grid.shape[1] // 2)
    r = client.get("/api/regions/jezero/cell", params={"lat": lat, "lon": lon})
    assert r.status_code == 200
    body = r.json()
    assert body["traversability"] in (0, 1, 2) and body["elevation_m"] is not None
    assert body["slope_deg"] >= 0 and body["roughness_m"] >= 0


def test_cell_query_longitude_convention(client, grid):
    lon, lat = grid.to_lonlat(50, 50)
    ok = client.get("/api/regions/jezero/cell", params={"lat": lat, "lon": lon})
    assert ok.status_code == 200 and ok.json()["lon"] == pytest.approx(lon)
    # 282.5 °E equivale a −77.5: es otro lugar, fuera de la región (no se confunde con 77.5).
    other = client.get("/api/regions/jezero/cell", params={"lat": lat, "lon": 282.5})
    assert other.status_code == 422 and other.json()["code"] == "out_of_region"
    # Fuera del rango admitido (−180..360) se rechaza por validación.
    assert (
        client.get("/api/regions/jezero/cell", params={"lat": lat, "lon": 437.0}).status_code == 422
    )


@pytest.mark.parametrize(
    "params", [{"lat": 0, "lon": 0}, {"lat": 18.4, "lon": 10}, {"lat": 18.4, "lon": 200}]
)
def test_cell_outside_region_is_422_with_message(client, params):
    r = client.get("/api/regions/jezero/cell", params=params)
    assert r.status_code == 422 and r.json()["code"] == "out_of_region" and r.json()["error"]


@pytest.mark.parametrize("params", [{"lat": 99, "lon": 77}, {"lat": "x", "lon": 77}, {"lat": 18}])
def test_cell_invalid_inputs(client, params):
    r = client.get("/api/regions/jezero/cell", params=params)
    assert r.status_code == 422 and set(r.json()) == {"error", "code"}


def test_registry_skips_declared_layers_missing_on_disk(data_dir, tmp_path):
    import shutil

    from marsmap.api.registry import Registry

    shutil.copytree(data_dir / "jezero", tmp_path / "jezero")
    (tmp_path / "jezero" / "roughness.tif").unlink()
    region = Registry(tmp_path).get("jezero")
    assert "roughness" not in region.layers and len(region.layers) == 4


def test_registry_skips_regions_without_processed_data(tmp_path):
    from marsmap.api.registry import Registry

    assert Registry(tmp_path).get("jezero") is None
