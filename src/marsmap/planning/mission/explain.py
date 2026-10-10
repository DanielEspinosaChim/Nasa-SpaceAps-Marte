"""Explicaciones con cifras de una misión: por qué se visita cada POI y por qué se descartan los demás."""

from __future__ import annotations

from marsmap.planning.mission.config import MissionConfig
from marsmap.planning.mission.legs import LegMatrix
from marsmap.planning.mission.objectives import evaluate_sequence
from marsmap.planning.mission.optimize import Mission
from marsmap.planning.mission.poi import PointOfInterest
from marsmap.planning.mission.prefilter import Discard


def _node_name(k: int, pois: list[PointOfInterest]) -> str:
    return "el hábitat" if k == 0 else pois[k - 1].name


def _best_insertion(seq, k, lm, pois, cfg):
    """Mejor inserción de k en la misión (menor energía extra) o None si ninguna tiene camino."""
    base = evaluate_sequence(seq, lm, pois, cfg)
    best = None
    for pos in range(len(seq) + 1):
        cand = (*seq[:pos], k, *seq[pos:])
        m = evaluate_sequence(cand, lm, pois, cfg)
        if m.n_missing_legs:
            continue
        if best is None or m.energy_wh < best[1].energy_wh:
            best = (cand, m)
    return base, best


def explain_mission(
    mission: Mission,
    lm: LegMatrix,
    pois: list[PointOfInterest],
    cfg: MissionConfig,
    energy_budget_wh: float,
    max_time_h: float,
    prefilter_discards: list[Discard],
) -> list[str]:
    seq = mission.sequence
    out: list[str] = []
    base = mission.metrics
    if not seq:
        out.append(
            "Misión vacía: ningún punto de interés cabe en el presupuesto de energía "
            f"({energy_budget_wh:.0f} Wh), el tiempo máximo ({max_time_h:.0f} h) o las "
            "restricciones de ruta; el rover permanece en el hábitat."
        )
    for idx, k in enumerate(seq):
        p = pois[k - 1]
        prev = 0 if idx == 0 else seq[idx - 1]
        without = evaluate_sequence(tuple(x for x in seq if x != k), lm, pois, cfg)
        out.append(
            f"Visita {p.name} (ciencia {p.science_value:.2f}, estudio de {p.dwell_time_h:.1f} h) "
            f"a {lm.distance_m[prev, k] / 1000:.1f} km {'del hábitat' if prev == 0 else 'de ' + _node_name(prev, pois)}. "
            f"Quitarlo ahorraría {base.energy_wh - without.energy_wh:.0f} Wh y "
            f"{base.time_h - without.time_h:.1f} h, pero perdería {p.science_value:.2f} de ciencia."
        )
    for k, p in enumerate(pois, start=1):
        if k in seq:
            continue
        _, best = _best_insertion(seq, k, lm, pois, cfg)
        if best is None:
            out.append(
                f"Descarta {p.name}: no existe un camino que cumpla las restricciones hasta ese sitio."
            )
            continue
        _, m = best
        d_e, d_t = m.energy_wh - base.energy_wh, m.time_h - base.time_h
        head = (
            f"Descarta {p.name}: añadirlo costaría +{d_e:.0f} Wh y +{d_t:.1f} h "
            f"por {p.science_value:.2f} de ciencia"
        )
        if m.energy_wh > energy_budget_wh:
            out.append(
                f"{head}, y la energía no alcanza ({m.energy_wh:.0f} Wh frente a un presupuesto "
                f"de {energy_budget_wh:.0f} Wh)."
            )
        elif m.time_h > max_time_h:
            out.append(
                f"{head}, y supera el tiempo máximo ({m.time_h:.0f} h frente a {max_time_h:.0f} h)."
            )
        else:
            out.append(
                f"{head} y +{m.risk_score - base.risk_score:.0f} de riesgo: cabe en el "
                "presupuesto, pero esta misión prioriza otro balance entre ciencia, tiempo y riesgo."
            )
    out.extend(f"Descarta: {d.reason}" for d in prefilter_discards)
    return out
