"""Convenciones de coordenadas de Marte usadas en todo el proyecto.

- Datum Mars 2000 (IAU), esfera de radio 3 396 190 m.
- Longitud interna −180..180, positiva al Este. Latitud planetocéntrica.
"""

from __future__ import annotations

import math

import numpy as np
from affine import Affine

MARS_RADIUS_M = 3_396_190.0
M_PER_DEG = math.pi * MARS_RADIUS_M / 180.0  # ≈ 59 274.7 m por grado de latitud

# CRS geográfico de Marte (esfera IAU 2000). Todas las capas procesadas usan este CRS.
MARS_GEO_CRS = "+proj=longlat +R=3396190 +no_defs +type=crs"


def normalize_lon(lon: float) -> float:
    """Convierte una longitud Este en 0..360 a −180..180.

    180 se conserva como 180 (y −180 como −180), para no cambiar el lado del
    antimeridiano de un valor que ya era válido.
    """
    lon = float(lon)
    if -180.0 <= lon <= 180.0:
        return lon
    wrapped = ((lon + 180.0) % 360.0) - 180.0
    return 180.0 if wrapped == -180.0 else wrapped


def cell_size_m(transform: Affine, lat_deg: np.ndarray | float) -> tuple[np.ndarray, float]:
    """Tamaño de celda en metros (dx, dy) para un raster en grados.

    dx se corrige por cos(latitud): `dx = |a| · M_PER_DEG · cos(lat)`.
    """
    dx = abs(transform.a) * M_PER_DEG * np.cos(np.radians(lat_deg))
    dy = abs(transform.e) * M_PER_DEG
    return np.asarray(dx, dtype=np.float64), float(dy)


def row_latitudes(transform: Affine, height: int) -> np.ndarray:
    """Latitud del centro de cada fila."""
    rows = np.arange(height) + 0.5
    return transform.f + rows * transform.e


def col_longitudes(transform: Affine, width: int) -> np.ndarray:
    """Longitud del centro de cada columna."""
    cols = np.arange(width) + 0.5
    return transform.c + cols * transform.a


def great_circle_m(lat1, lon1, lat2, lon2):
    """Distancia sobre la esfera de Marte (haversine), en metros. Acepta arrays."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * MARS_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def lonlat_to_rowcol(transform: Affine, lon: float, lat: float) -> tuple[int, int]:
    col, row = ~transform @ (normalize_lon(lon), lat)
    return int(math.floor(row)), int(math.floor(col))


def rowcol_to_lonlat(transform: Affine, row: int, col: int) -> tuple[float, float]:
    lon, lat = transform @ (col + 0.5, row + 0.5)
    return float(lon), float(lat)
