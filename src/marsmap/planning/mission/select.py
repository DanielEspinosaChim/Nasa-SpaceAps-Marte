"""Misiones con nombre y selector por pesos (el "switch de modelos" del panel)."""

from __future__ import annotations

import numpy as np

from marsmap.planning.mission.optimize import Mission

NAMES = ("safe", "fast", "science", "balanced")
_TIE = 1e-6  # desempate: entre iguales gana la de menor suma de objetivos normalizados


def normalized_objectives(front: list[Mission]) -> np.ndarray:
    """(m, 3) con (−ciencia, tiempo, riesgo) normalizados a [0,1] por min-max dentro del frente."""
    F = np.array([m.metrics.objectives() for m in front], dtype=float)
    span = np.ptp(F, axis=0)
    return (F - F.min(axis=0)) / np.where(span > 0, span, 1.0)


def validate_weights(weights: dict) -> tuple[float, float, float]:
    try:
        vals = (float(weights["safety"]), float(weights["science"]), float(weights["speed"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("los pesos requieren safety, science y speed numéricos") from exc
    if any(not 0.0 <= v <= 1.0 for v in vals):
        raise ValueError("cada peso debe estar entre 0 y 1")
    if sum(vals) <= 0:
        raise ValueError("al menos un peso debe ser mayor que 0")
    return vals


def select_mission(front: list[Mission], weights: dict) -> Mission:
    """Misión del frente que minimiza la suma ponderada de objetivos normalizados."""
    w_safe, w_sci, w_speed = validate_weights(weights)
    if not front:
        raise ValueError("el frente está vacío")
    Fn = normalized_objectives(front)
    score = Fn @ np.array([w_sci, w_speed, w_safe]) + _TIE * Fn.sum(axis=1)
    return front[int(np.argmin(score))]  # argmin devuelve el primero: orden estable del frente


def name_missions(front: list[Mission]) -> dict[str, str]:
    """`safe`, `fast`, `science` (extremos) y `balanced` (punto de rodilla) → mission_id."""
    pure = {
        "safe": {"safety": 1, "science": 0, "speed": 0},
        "fast": {"safety": 0, "science": 0, "speed": 1},
        "science": {"safety": 0, "science": 1, "speed": 0},
    }
    named = {k: select_mission(front, w).mission_id for k, w in pure.items()}
    Fn = normalized_objectives(front)
    named["balanced"] = front[int(np.argmin(np.linalg.norm(Fn, axis=1)))].mission_id
    return named
