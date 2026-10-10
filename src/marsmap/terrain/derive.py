"""Capas derivadas del DEM: pendiente, rugosidad, sombreado y transitabilidad.

Todas las funciones reciben la elevación como float64/float32 con NaN en
nodata, y propagan NaN: una celda sin dato (o con un vecino sin dato en la
ventana 3×3) nunca se trata como terreno plano ni seguro.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter

SLOPE_SAFE_DEG = 10.0  # Perseverance: < 10° seguro
SLOPE_BLOCKED_DEG = 15.0  # > 15° bloqueado
TRAV_SAFE, TRAV_RISK, TRAV_BLOCKED, TRAV_NODATA = 0, 1, 2, 255
HILLSHADE_NODATA = 0


def _neighbors(z: np.ndarray) -> dict[str, np.ndarray]:
    """Vecinos 3×3 con borde replicado (a b c / d e f / g h i)."""
    p = np.pad(z, 1, mode="edge")
    h, w = z.shape
    return {
        "a": p[0:h, 0:w], "b": p[0:h, 1 : w + 1], "c": p[0:h, 2 : w + 2],
        "d": p[1 : h + 1, 0:w], "f": p[1 : h + 1, 2 : w + 2],
        "g": p[2 : h + 2, 0:w], "h": p[2 : h + 2, 1 : w + 1], "i": p[2 : h + 2, 2 : w + 2],
    }  # fmt: skip


def gradient_horn(z: np.ndarray, dx_m: np.ndarray | float, dy_m: float):
    """Gradiente de Horn (dz/dx Este, dz/dy Norte) en m/m.

    `dx_m` puede ser un escalar o un vector por fila (corrección por latitud).
    Se asume la fila 0 al Norte (transformación con `e < 0`).
    """
    z = np.asarray(z, dtype=np.float64)
    n = _neighbors(z)
    dx = np.asarray(dx_m, dtype=np.float64)
    if dx.ndim == 1:
        dx = dx[:, None]
    dzdx = ((n["c"] + 2 * n["f"] + n["i"]) - (n["a"] + 2 * n["d"] + n["g"])) / (8 * dx)
    # Fila 0 al Norte: "arriba" (a b c) es Norte.
    dzdy = ((n["a"] + 2 * n["b"] + n["c"]) - (n["g"] + 2 * n["h"] + n["i"])) / (8 * dy_m)
    return dzdx, dzdy


def slope_deg(z: np.ndarray, dx_m: np.ndarray | float, dy_m: float) -> np.ndarray:
    dzdx, dzdy = gradient_horn(z, dx_m, dy_m)
    out = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    # Horn no usa la celda central: sin esto, un hueco aislado parecería terreno válido.
    out[np.isnan(np.asarray(z, dtype=np.float64))] = np.nan
    return out.astype(np.float32)


def roughness(z: np.ndarray) -> np.ndarray:
    """Desviación estándar de la elevación en una ventana 3×3 (m)."""
    z = np.asarray(z, dtype=np.float64)
    # Restar la media global evita pérdida de precisión en z² con elevaciones grandes.
    offset = np.nanmean(z) if np.isfinite(z).any() else 0.0
    zc = z - offset
    mean = uniform_filter(zc, size=3, mode="nearest")
    mean_sq = uniform_filter(zc * zc, size=3, mode="nearest")
    var = np.clip(mean_sq - mean * mean, 0.0, None)
    return np.sqrt(var).astype(np.float32)


def hillshade(
    z: np.ndarray,
    dx_m: np.ndarray | float,
    dy_m: float,
    azimuth_deg: float = 315.0,
    altitude_deg: float = 45.0,
) -> np.ndarray:
    """Sombreado del relieve en uint8 1–255; 0 = nodata."""
    dzdx, dzdy = gradient_horn(z, dx_m, dy_m)
    slope = np.arctan(np.hypot(dzdx, dzdy))
    # Aspecto: dirección de máxima bajada, medida en sentido horario desde el Norte.
    aspect = np.arctan2(-dzdx, -dzdy)
    az = np.radians(azimuth_deg)
    alt = np.radians(altitude_deg)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    out = np.clip(shade, 0.0, 1.0) * 254.0 + 1.0
    out = np.where(
        np.isfinite(out) & ~np.isnan(np.asarray(z, dtype=np.float64)), out, HILLSHADE_NODATA
    )
    return np.round(out).astype(np.uint8)


def traversability(slope: np.ndarray) -> np.ndarray:
    """0 segura (< 10°), 1 riesgo (10°–15°), 2 bloqueada (> 15°), 255 nodata."""
    s = np.asarray(slope, dtype=np.float64)
    out = np.full(s.shape, TRAV_NODATA, dtype=np.uint8)
    valid = np.isfinite(s)
    out[valid & (s < SLOPE_SAFE_DEG)] = TRAV_SAFE
    out[valid & (s >= SLOPE_SAFE_DEG) & (s <= SLOPE_BLOCKED_DEG)] = TRAV_RISK
    out[valid & (s > SLOPE_BLOCKED_DEG)] = TRAV_BLOCKED
    return out
