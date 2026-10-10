"""Explicaciones en lenguaje natural de una ruta, con cifras (plantillas del servidor)."""

from __future__ import annotations

import numpy as np

from marsmap.planning.costmap import CostMap
from marsmap.planning.metrics import RouteMetrics, straight_line_cells
from marsmap.terrain.derive import SLOPE_BLOCKED_DEG, SLOPE_SAFE_DEG


def _fmt_m(m: float) -> str:
    return f"{m / 1000:.1f} km" if m >= 1000 else f"{m:.0f} m"


def explain_route(cm: CostMap, cells: list[tuple[int, int]], m: RouteMetrics) -> list[str]:
    out: list[str] = []
    safe_pct = 100.0 - m.pct_risk_cells
    out.append(
        f"El {safe_pct:.0f}% del recorrido está en terreno seguro "
        f"(pendiente < {SLOPE_SAFE_DEG:.0f}°); la pendiente máxima es {m.max_slope_deg:.1f}° "
        f"(límite de bloqueo {SLOPE_BLOCKED_DEG:.0f}°)."
    )

    line = straight_line_cells(cells[0], cells[-1])
    arr = np.asarray(line)
    on_line_blocked = cm.blocked[arr[:, 0], arr[:, 1]]
    if on_line_blocked.any():
        n_blocked = int(on_line_blocked.sum())
        first = int(np.argmax(on_line_blocked))
        frac = first / max(1, len(line) - 1)
        worst = float(cm.slope[arr[:, 0][on_line_blocked], arr[:, 1][on_line_blocked]].max())
        detour = m.distance_m - m.straight_line_m
        out.append(
            f"La línea recta cruzaría {n_blocked} celdas bloqueadas (pendiente de hasta "
            f"{worst:.0f}°, a {_fmt_m(frac * m.straight_line_m)} del inicio); la ruta las evita "
            f"con un desvío de {_fmt_m(max(detour, 0.0))} (+{(m.tortuosity - 1) * 100:.0f}%)."
        )
    elif m.tortuosity > 1.15:
        out.append(
            f"Rodea terreno costoso: recorre {_fmt_m(m.distance_m)} frente a "
            f"{_fmt_m(m.straight_line_m)} en línea recta (tortuosidad {m.tortuosity:.2f})."
        )
    else:
        out.append(
            f"Sigue casi la línea recta: {_fmt_m(m.distance_m)} frente a "
            f"{_fmt_m(m.straight_line_m)} (tortuosidad {m.tortuosity:.2f})."
        )

    if m.risk_m > 0:
        out.append(
            f"Cruza {_fmt_m(m.risk_m)} de terreno de riesgo ({SLOPE_SAFE_DEG:.0f}°–"
            f"{SLOPE_BLOCKED_DEG:.0f}°), donde se estima la mitad de velocidad."
        )
    out.append(
        f"Desnivel acumulado: +{m.elevation_gain_m:.0f} m / −{m.elevation_loss_m:.0f} m; "
        f"tiempo estimado {m.est_time_h:.1f} h."
    )
    return out
