"""Terreno sintético determinista con la misma interfaz que un DEM real.

Sirve para desarrollar, probar y hacer la demo sin red ni datos de NASA. El
resultado depende solo de `(bbox, resolution_m, seed)`.
"""

from __future__ import annotations

import numpy as np
from affine import Affine

from marsmap.geo.coords import M_PER_DEG, col_longitudes, row_latitudes

BASE_ELEVATION_M = -2500.0


def grid_for_bbox(bbox, resolution_m: float = 200.0) -> tuple[Affine, int, int]:
    """Malla lon/lat con píxel cuadrado en grados (como un DEM equirectangular)."""
    lon_min, lat_min, lon_max, lat_max = bbox
    deg = resolution_m / M_PER_DEG
    width = max(3, int(round((lon_max - lon_min) / deg)))
    height = max(3, int(round((lat_max - lat_min) / deg)))
    transform = Affine(
        (lon_max - lon_min) / width, 0.0, lon_min, 0.0, -(lat_max - lat_min) / height, lat_max
    )
    return transform, height, width


def _local_xy_m(transform: Affine, height: int, width: int):
    """Coordenadas locales en metros (x Este, y Norte) respecto a la esquina NO."""
    lats = row_latitudes(transform, height)
    lons = col_longitudes(transform, width)
    lat0 = float(np.mean(lats))
    x = (lons - lons[0])[None, :] * M_PER_DEG * np.cos(np.radians(lat0))
    y = (lats - lats[0])[:, None] * M_PER_DEG
    return np.broadcast_to(x, (height, width)), np.broadcast_to(y, (height, width))


def _crater(x, y, cx, cy, radius, depth, rim_h, rim_w=0.25, breaches=()):
    """Cráter con borde elevado. `breaches` son ángulos (rad) donde el borde se abre (como
    la entrada y la salida del antiguo río de Jezero), para que el interior sea accesible."""
    r = np.hypot(x - cx, y - cy) / radius
    bowl = np.where(r < 1.0, depth * (r * r - 1.0), 0.0)
    rim = rim_h * np.exp(-(((r - 1.0) / rim_w) ** 2))
    if breaches:
        theta = np.arctan2(y - cy, x - cx)
        gap = sum(
            np.exp(-(((((theta - b + np.pi) % (2 * np.pi)) - np.pi) / 0.35) ** 2)) for b in breaches
        )
        rim = rim * (1.0 - 0.95 * np.clip(gap, 0.0, 1.0))
    return bowl + rim


def _fractal_noise(rng: np.random.Generator, shape, beta: float = 2.2) -> np.ndarray:
    """Ruido 1/f^beta por síntesis espectral, normalizado a desviación 1."""
    h, w = shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    f = np.hypot(fx, fy)
    f[0, 0] = 1.0
    amp = f ** (-beta / 2.0)
    amp[0, 0] = 0.0
    phase = rng.uniform(0, 2 * np.pi, size=amp.shape)
    spec = amp * np.exp(1j * phase)
    field = np.fft.irfft2(spec, s=(h, w))
    return (field - field.mean()) / (field.std() + 1e-12)


def generate_dem(bbox, resolution_m: float = 200.0, seed: int = 42):
    """DEM sintético: cráter principal con delta, cráteres pequeños, colinas y ruido.

    Devuelve `(elevation_float32, transform, height, width)`.
    """
    rng = np.random.default_rng(seed)
    transform, height, width = grid_for_bbox(bbox, resolution_m)
    x, y = _local_xy_m(transform, height, width)
    w_m, h_m = float(x.max()), float(y.min())  # y crece hacia el Sur (negativo)

    z = np.full((height, width), BASE_ELEVATION_M, dtype=np.float64)
    # Cráter principal (tipo Jezero): ~ 40% del ancho, borde interior empinado.
    cx, cy = 0.58 * w_m, 0.55 * h_m
    radius = 0.38 * min(w_m, -h_m)
    z += _crater(x, y, cx, cy, radius, depth=450.0, rim_h=420.0, rim_w=0.08, breaches=(0.0, np.pi))
    # Delta: lóbulo elevado y suave pegado al borde occidental interior.
    dx, dy = cx - 0.72 * radius, cy + 0.10 * radius
    z += 160.0 * np.exp(-(((x - dx) / (0.28 * radius)) ** 2 + ((y - dy) / (0.22 * radius)) ** 2))
    # Cráteres pequeños.
    for _ in range(int(rng.integers(18, 28))):
        r_k = float(rng.uniform(500.0, 3500.0))
        z += _crater(
            x, y,
            float(rng.uniform(0, w_m)), float(rng.uniform(h_m, 0)),
            r_k, depth=0.10 * r_k, rim_h=0.03 * r_k,
        )  # fmt: skip
    # Colinas suaves.
    for _ in range(int(rng.integers(4, 8))):
        sx = float(rng.uniform(2000.0, 8000.0))
        z += float(rng.uniform(40.0, 180.0)) * np.exp(
            -(((x - rng.uniform(0, w_m)) / sx) ** 2 + ((y - rng.uniform(h_m, 0)) / sx) ** 2)
        )
    z += 5.0 * _fractal_noise(rng, (height, width))
    return z.astype(np.float32), transform, height, width


def generate_pois(bbox, n: int, seed: int = 0, margin: float = 0.05) -> list[dict]:
    """Puntos de interés sintéticos deterministas dentro del bbox (para tests y demo)."""
    rng = np.random.default_rng(seed)
    lon_min, lat_min, lon_max, lat_max = bbox
    mx, my = (lon_max - lon_min) * margin, (lat_max - lat_min) * margin
    categories = ["delta", "crater_rim", "outcrop", "dune", "fan"]
    out = []
    for k in range(n):
        out.append(
            {
                "poi_id": f"syn_{k:02d}",
                "name": f"Sitio sintético {k + 1}",
                "lon": float(rng.uniform(lon_min + mx, lon_max - mx)),
                "lat": float(rng.uniform(lat_min + my, lat_max - my)),
                "science_value": float(np.round(rng.uniform(0.1, 1.0), 3)),
                "dwell_time_h": float(np.round(rng.uniform(0.5, 3.0), 2)),
                "category": categories[k % len(categories)],
                "rationale": "Punto generado para pruebas; sin valor científico real.",
                "source": "synthetic",
            }
        )
    return out
