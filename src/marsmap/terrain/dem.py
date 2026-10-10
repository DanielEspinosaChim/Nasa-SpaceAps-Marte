"""Lectura de una ventana de un DEM real (GeoTIFF/IMG) reproyectada a lon/lat de Marte."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import rasterio
from affine import Affine
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds

from marsmap.geo.coords import M_PER_DEG, MARS_GEO_CRS
from marsmap.terrain.synthetic import grid_for_bbox


class DemCoverageError(ValueError):
    """El bbox pedido no está cubierto por el DEM."""


@dataclass
class DemWindow:
    elevation: np.ndarray  # float32, NaN = nodata
    transform: Affine
    crs: str
    resolution_m: float


def native_resolution_m(src) -> float:
    res = abs(src.res[0])
    return res * M_PER_DEG if src.crs is not None and src.crs.is_geographic else res


def read_dem_window(path: str, bbox, resolution_m: float | None = None) -> DemWindow:
    """Lee solo el bbox del DEM (sin cargar el archivo global) en el CRS lon/lat de Marte."""
    with rasterio.open(path) as src:
        if src.crs is None:
            raise ValueError("el DEM no tiene CRS; no se puede georreferenciar")
        left, bottom, right, top = transform_bounds(src.crs, MARS_GEO_CRS, *src.bounds)
        lon_min, lat_min, lon_max, lat_max = bbox
        if lon_min < left or lon_max > right or lat_min < bottom or lat_max > top:
            raise DemCoverageError(
                f"el bbox {list(bbox)} está fuera de la cobertura del DEM "
                f"[{left:.3f}, {bottom:.3f}, {right:.3f}, {top:.3f}]"
            )
        res_m = resolution_m or native_resolution_m(src)
        transform, height, width = grid_for_bbox(bbox, res_m)
        with WarpedVRT(
            src,
            crs=MARS_GEO_CRS,
            transform=transform,
            width=width,
            height=height,
            resampling=Resampling.bilinear,
            src_nodata=src.nodata,
            nodata=np.nan,
            dtype="float32",
        ) as vrt:
            z = vrt.read(1).astype(np.float32)
        if src.nodata is not None and not np.isnan(src.nodata):
            z[z == np.float32(src.nodata)] = np.nan
    if not np.isfinite(z).any():
        raise DemCoverageError("la ventana del DEM no tiene ningún dato válido")
    return DemWindow(elevation=z, transform=transform, crs=MARS_GEO_CRS, resolution_m=float(res_m))
