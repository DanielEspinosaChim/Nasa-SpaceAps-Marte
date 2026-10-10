"""Coloreado de capas a PNG (nodata transparente) y leyendas."""

from __future__ import annotations

import io

import numpy as np
import rasterio
from PIL import Image

from marsmap.terrain.derive import TRAV_NODATA

TRAV_COLORS = {0: "#3fa34d", 1: "#f2c14e", 2: "#d1495b"}
TRAV_LABELS = {0: "Segura (< 10°)", 1: "Riesgo (10°–15°)", 2: "Bloqueada (> 15°)"}
# Rampa de elevación/pendiente/rugosidad (viridis simplificada, 5 paradas).
RAMP = ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"]
RAMP_LAYERS = {"elevation": "m", "slope": "°", "roughness": "m"}


def _hex(c: str) -> tuple[int, int, int]:
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def _ramp(t: np.ndarray) -> np.ndarray:
    stops = np.array([_hex(c) for c in RAMP], dtype=float)
    pos = np.clip(t, 0, 1) * (len(stops) - 1)
    lo = np.floor(pos).astype(int).clip(0, len(stops) - 2)
    frac = (pos - lo)[..., None]
    return stops[lo] * (1 - frac) + stops[lo + 1] * frac


def value_range(layer_id: str, data: np.ndarray) -> tuple[float, float]:
    if layer_id == "slope":
        return 0.0, 20.0
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        return 0.0, 1.0
    lo, hi = np.percentile(finite, [2, 98])
    return (float(lo), float(hi if hi > lo else lo + 1.0))


def render_png(layer_id: str, path) -> bytes:
    with rasterio.open(path) as ds:
        data = ds.read(1)
    h, w = data.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    if layer_id == "traversability":
        for v, color in TRAV_COLORS.items():
            m = data == v
            rgba[m, :3], rgba[m, 3] = _hex(color), 210
    elif layer_id == "hillshade":
        valid = data > 0
        rgba[..., :3] = data[..., None]
        rgba[..., 3] = np.where(valid, 255, 0)
    else:
        lo, hi = value_range(layer_id, data.astype(float))
        valid = np.isfinite(data)
        rgb = _ramp((np.nan_to_num(data.astype(float), nan=lo) - lo) / (hi - lo))
        rgba[..., :3] = rgb.astype(np.uint8)
        rgba[..., 3] = np.where(valid, 220, 0)
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, format="PNG")
    return buf.getvalue()


def legend(layer_id: str, path) -> list[dict]:
    if layer_id == "traversability":
        return [
            {"value": float(v), "color": TRAV_COLORS[v], "label": TRAV_LABELS[v]} for v in (0, 1, 2)
        ]
    if layer_id == "hillshade":
        return [
            {"value": 0.0, "color": "#000000", "label": "Sombra"},
            {"value": 255.0, "color": "#ffffff", "label": "Luz"},
        ]
    with rasterio.open(path) as ds:
        data = ds.read(1).astype(float)
    lo, hi = value_range(layer_id, data)
    unit = RAMP_LAYERS.get(layer_id, "")
    return [
        {"value": float(v), "color": c, "label": f"{v:.1f} {unit}".strip()}
        for v, c in zip(np.linspace(lo, hi, len(RAMP)), RAMP, strict=True)
    ]


def sample(path, row: int, col: int):
    with rasterio.open(path) as ds:
        win = rasterio.windows.Window(col, row, 1, 1)
        return ds.read(1, window=win)[0, 0], ds.nodata


def is_nodata(layer_id: str, value) -> bool:
    if layer_id == "traversability":
        return int(value) == TRAV_NODATA
    if layer_id == "hillshade":
        return int(value) == 0
    return not np.isfinite(value)
