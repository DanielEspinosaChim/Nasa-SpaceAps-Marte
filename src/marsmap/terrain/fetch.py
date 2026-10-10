"""Recorta el bbox de una región de un DEM remoto o local y lo guarda en `data/raw/<region>/`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

import rasterio
from rasterio.transform import array_bounds
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

from marsmap.config.regions import get_region
from marsmap.geo.coords import MARS_GEO_CRS

ALLOWED_SUFFIXES = (".usgs.gov", ".nasa.gov", ".wustl.edu")
PADDING_DEG = 0.02  # margen para que el borde de la región tenga vecinos al derivar la pendiente


def check_url(url: str) -> str:
    u = urlparse(url)
    host = (u.hostname or "").lower()
    if u.scheme != "https" or not any(host == s[1:] or host.endswith(s) for s in ALLOWED_SUFFIXES):
        raise ValueError(
            f"URL no permitida: solo https hacia {', '.join('*' + s for s in ALLOWED_SUFFIXES)}"
        )
    return url


def crop(source: str, bbox, out_path: Path) -> Path:
    """Escribe el recorte (con margen) en `out_path`, en el CRS original del DEM."""
    path = f"/vsicurl/{source}" if source.startswith("https://") else source
    lon_min, lat_min, lon_max, lat_max = bbox
    with rasterio.open(path) as src:
        if src.crs is None:
            raise ValueError("el DEM no tiene CRS")
        b = transform_bounds(
            MARS_GEO_CRS,
            src.crs,
            lon_min - PADDING_DEG, lat_min - PADDING_DEG, lon_max + PADDING_DEG, lat_max + PADDING_DEG,
        )  # fmt: skip
        left, bottom, right, top = src.bounds
        if b[0] < left or b[2] > right or b[1] < bottom or b[3] > top:
            raise ValueError("la región queda fuera de la cobertura del DEM")
        win = from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
        data = src.read(1, window=win)
        transform = src.window_transform(win)
        profile = src.profile | {
            "driver": "GTiff", "height": data.shape[0], "width": data.shape[1],
            "transform": transform, "count": 1, "compress": "deflate",
        }  # fmt: skip
        profile.pop("blockxsize", None), profile.pop("blockysize", None), profile.pop("tiled", None)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp")
    with rasterio.open(tmp, "w", **profile) as dst:
        dst.write(data, 1)
    tmp.replace(out_path)
    assert array_bounds(data.shape[0], data.shape[1], transform)
    return out_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--region", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--url", help="GeoTIFF remoto (https, dominios NASA/USGS/WUSTL)")
    g.add_argument("--source", help="DEM local ya descargado")
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    try:
        region = get_region(a.region)
        src = check_url(a.url) if a.url else a.source
        out = a.out or Path("data/raw") / region.region_id / "dem.tif"
        crop(src, region.bbox, out)
    except (KeyError, ValueError, rasterio.errors.RasterioIOError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"recorte guardado en {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
