"""Carga de las capas de una región como una malla en memoria para planificar."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine

from marsmap.geo.coords import cell_size_m, lonlat_to_rowcol, row_latitudes, rowcol_to_lonlat
from marsmap.terrain.build import derive_layers


@dataclass
class TerrainGrid:
    elevation: np.ndarray  # float64, NaN = nodata
    slope: np.ndarray  # float64 grados
    roughness: np.ndarray  # float64 m
    traversability: np.ndarray  # uint8
    transform: Affine

    @property
    def shape(self) -> tuple[int, int]:
        return self.elevation.shape

    @property
    def dx_m(self) -> np.ndarray:
        """Tamaño de celda Este-Oeste por fila (m)."""
        return cell_size_m(self.transform, row_latitudes(self.transform, self.shape[0]))[0]

    @property
    def dy_m(self) -> float:
        return cell_size_m(self.transform, 0.0)[1]

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        h, w = self.shape
        t = self.transform
        return (t.c, t.f + h * t.e, t.c + w * t.a, t.f)

    def to_rowcol(self, lat: float, lon: float) -> tuple[int, int] | None:
        r, c = lonlat_to_rowcol(self.transform, lon, lat)
        h, w = self.shape
        return (r, c) if 0 <= r < h and 0 <= c < w else None

    def to_lonlat(self, r: int, c: int) -> tuple[float, float]:
        return rowcol_to_lonlat(self.transform, r, c)

    def cell_centers(self) -> tuple[np.ndarray, np.ndarray]:
        """Arrays (lat, lon) de los centros de celda, forma (h, w)."""
        h, w = self.shape
        cols, rows = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
        lon, lat = self.transform @ (cols, rows)
        return np.asarray(lat), np.asarray(lon)


def load_grid(folder: Path) -> TerrainGrid:
    def read(name):
        with rasterio.open(folder / f"{name}.tif") as ds:
            return ds.read(1), ds.transform

    elev, t = read("elevation")
    slope, _ = read("slope")
    rough, _ = read("roughness")
    trav, _ = read("traversability")
    return TerrainGrid(
        elevation=elev.astype(np.float64),
        slope=slope.astype(np.float64),
        roughness=rough.astype(np.float64),
        traversability=trav,
        transform=t,
    )


def grid_from_dem(z: np.ndarray, transform: Affine) -> TerrainGrid:
    """Malla desde un DEM en memoria (tests y terreno sintético)."""
    layers = derive_layers(np.asarray(z, dtype=np.float32), transform)
    return TerrainGrid(
        elevation=layers["elevation"].astype(np.float64),
        slope=layers["slope"].astype(np.float64),
        roughness=layers["roughness"].astype(np.float64),
        traversability=layers["traversability"],
        transform=transform,
    )
