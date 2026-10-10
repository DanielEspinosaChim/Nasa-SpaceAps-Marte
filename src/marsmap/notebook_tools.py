"""Funciones de datos y gráficos para el notebook de demostración (sin lógica de negocio nueva).

Todo lo que se dibuja sale de los datos reales de NASA (DEM MOLA–HRSC, waypoints y sitios de
muestras de Mars 2020) y de los módulos del proyecto (A*, genético). Cada función devuelve una
figura de matplotlib.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import ListedColormap

from marsmap.geo.coords import M_PER_DEG, great_circle_m
from marsmap.planning.astar import astar
from marsmap.planning.costmap import build_costmap
from marsmap.planning.dijkstra import dijkstra
from marsmap.planning.mission.baselines.bruteforce import best_science
from marsmap.planning.mission.config import MissionConfig, load_config
from marsmap.planning.mission.objectives import evaluate_sequence
from marsmap.planning.mission.poi import PointOfInterest, load_pois
from marsmap.planning.mission.service import MissionPlan, plan_missions
from marsmap.planning.presets import PRESETS
from marsmap.planning.service import RouteError, plan_route
from marsmap.planning.terrain_grid import TerrainGrid, load_grid

# Paleta consistente con la app.
C_SAFE, C_RISK, C_BLOCK = "#3fa34d", "#f2c14e", "#d1495b"
C_ACCENT, C_NASA, C_OURS = "#e2672b", "#1d6fb8", "#e2672b"
LABELS = {"safe": "Segura", "fast": "Rápida", "science": "Científica", "balanced": "Balanceada"}


def project_root() -> Path:
    """Sube desde el directorio actual hasta encontrar pyproject.toml."""
    p = Path.cwd().resolve()
    for cand in (p, *p.parents):
        if (cand / "pyproject.toml").is_file():
            return cand
    raise FileNotFoundError("no se encontró la raíz del proyecto (pyproject.toml)")


@dataclass
class Ctx:
    root: Path
    grid: TerrainGrid
    hillshade: np.ndarray
    pois: list[PointOfInterest]
    hab: tuple[float, float]  # (lat, lon) del aterrizaje publicado por NASA
    wp_sol: np.ndarray  # waypoints reales ordenados por odómetro
    wp_odo_m: np.ndarray
    wp_lon: np.ndarray
    wp_lat: np.ndarray
    cfg: MissionConfig
    extent: tuple[float, float, float, float]  # w, e, s, n
    zoom: tuple[float, float, float, float]  # w, e, s, n de la zona donde ocurre la acción
    extra: dict = field(default_factory=dict)


def load_context(root: Path | None = None) -> Ctx:
    root = root or project_root()
    proc = root / "data" / "processed" / "jezero"
    raw = root / "data" / "raw" / "jezero" / "mars2020"
    for need in (proc / "elevation.tif", proc / "poi.geojson", raw / "M20_waypoints.json"):
        if not need.is_file():
            raise FileNotFoundError(f"falta {need}; ver data/README.md para generarlo")
    grid = load_grid(proc)
    with rasterio.open(proc / "hillshade.tif") as ds:
        hs = ds.read(1)
    meta = json.loads((proc / "poi.geojson").read_text(encoding="utf-8"))
    hab = (meta["landing_site"]["lat"], meta["landing_site"]["lon"])
    wp = json.loads((raw / "M20_waypoints.json").read_text(encoding="utf-8"))["features"]
    props = sorted((f["properties"] for f in wp), key=lambda p: (p["sol"], p["dist_total_m"]))
    w, s, e, n = grid.bbox
    pois = load_pois(proc / "poi.geojson")
    lon_wp = np.array([p["lon"] for p in props], dtype=float)
    lat_wp = np.array([p["lat"] for p in props], dtype=float)
    near_wp = great_circle_m(hab[0], hab[1], lat_wp, lon_wp) <= 11_000
    near_poi = [p for p in pois if great_circle_m(hab[0], hab[1], p.lat, p.lon) <= 11_000]
    xs = np.concatenate([lon_wp[near_wp], [p.lon for p in near_poi], [hab[1]]])
    ys = np.concatenate([lat_wp[near_wp], [p.lat for p in near_poi], [hab[0]]])
    pad = 0.025
    zoom = (xs.min() - pad, xs.max() + pad, ys.min() - pad, ys.max() + pad)
    return Ctx(
        root, grid, hs, pois, hab,
        np.array([p["sol"] for p in props], dtype=float),
        np.array([p["dist_total_m"] for p in props], dtype=float),
        lon_wp, lat_wp,
        load_config(), (w, e, s, n), zoom,
    )  # fmt: skip


# --- helpers de datos --------------------------------------------------------------------------
def first_sol(p: PointOfInterest) -> int | None:
    m = re.search(r"\d+", p.sol or "")
    return int(m.group()) if m else None


def odometer_m(ctx: Ctx, sol: int) -> float:
    """Odómetro real de Perseverance (metros recorridos) al final de ese sol."""
    i = int(np.searchsorted(ctx.wp_sol, sol, side="right")) - 1
    return float(ctx.wp_odo_m[max(i, 0)])


def nasa_path_until(ctx: Ctx, sol: int | None = None):
    keep = np.ones_like(ctx.wp_sol, dtype=bool) if sol is None else ctx.wp_sol <= sol
    return ctx.wp_lon[keep], ctx.wp_lat[keep]


def circle_lonlat(lat: float, lon: float, radius_m: float, n: int = 120):
    t = np.linspace(0, 2 * np.pi, n)
    kx = M_PER_DEG * np.cos(np.radians(lat))
    return lon + radius_m * np.cos(t) / kx, lat + radius_m * np.sin(t) / M_PER_DEG


def _base_ax(ctx: Ctx, ax, title: str, background: str = "hillshade", zoom: bool = False):
    w, e, s, n = ctx.extent
    ax.imshow(ctx.hillshade, extent=(w, e, s, n), cmap="gray", vmin=0, vmax=255, origin="upper")
    if background == "slope":
        im = ax.imshow(
            ctx.grid.slope, extent=(w, e, s, n), cmap="YlOrRd", vmin=0, vmax=20,
            origin="upper", alpha=0.8,
        )  # fmt: skip
        plt.colorbar(im, ax=ax, fraction=0.04, label="pendiente (°)")
    zw, ze, zs, zn = ctx.zoom if zoom else (w, e, s, n)
    ax.set_xlim(zw, ze)
    ax.set_ylim(zs, zn)
    ax.set_aspect(1 / np.cos(np.radians((zs + zn) / 2)))
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_xlabel("longitud (°E)")
    ax.set_ylabel("latitud (°N)")
    return ax


def _mark_habitat(ctx: Ctx, ax, walkback_m: float | None = 10_000.0):
    ax.plot(ctx.hab[1], ctx.hab[0], marker="*", ms=16, color="white", mec="black", zorder=6)
    ax.annotate("Aterrizaje", (ctx.hab[1], ctx.hab[0]), xytext=(8, -16), textcoords="offset points",
                color="white", fontsize=9, weight="bold", zorder=6,
                bbox={"boxstyle": "round,pad=0.15", "fc": "black", "alpha": 0.5, "lw": 0})  # fmt: skip
    if walkback_m:
        x, y = circle_lonlat(ctx.hab[0], ctx.hab[1], walkback_m)
        ax.plot(x, y, "--", color="#7aa7ff", lw=1.5, zorder=5, label="límite de walkback (10 km)")


# --- 1) lo que hizo NASA ----------------------------------------------------------------------
def fig_nasa_overview(ctx: Ctx):
    """Izquierda: la región completa. Derecha: zoom a donde trabajó Perseverance (datos reales)."""
    from matplotlib.patches import Rectangle

    fig, axes = plt.subplots(1, 2, figsize=(16, 7.5), gridspec_kw={"width_ratios": [1, 1.15]})
    w, e, s, n = ctx.extent
    zw, ze, zs, zn = ctx.zoom
    _base_ax(ctx, axes[0], "La región: cráter Jezero (DEM real MOLA–HRSC)")
    im = axes[0].imshow(
        ctx.grid.elevation, extent=(w, e, s, n), cmap="terrain", alpha=0.45, origin="upper"
    )
    plt.colorbar(im, ax=axes[0], fraction=0.045, pad=0.02, label="elevación (m)")
    axes[0].add_patch(Rectangle((zw, zs), ze - zw, zn - zs, fill=False, ec="#e2672b", lw=2))
    axes[0].annotate("zona ampliada →", (ze, zn), xytext=(6, 4), textcoords="offset points",
                     color="#e2672b", fontsize=9, weight="bold")  # fmt: skip

    ax = axes[1]
    _base_ax(ctx, ax, "Lo que hizo NASA: recorrido real y sitios de muestras", zoom=True)
    ax.plot(
        ctx.wp_lon,
        ctx.wp_lat,
        "-",
        color="white",
        lw=2.4,
        zorder=4,
        label="recorrido real (waypoints NASA)",
    )
    sites = sorted((p for p in ctx.pois if first_sol(p)), key=first_sol)
    sc = ax.scatter([p.lon for p in sites], [p.lat for p in sites], c=[first_sol(p) for p in sites],
                    cmap="plasma", s=90, ec="black", zorder=7, label="sitios de muestras")  # fmt: skip
    plt.colorbar(sc, ax=ax, fraction=0.045, pad=0.02, label="sol en que se tomó la muestra")
    _mark_habitat(ctx, ax)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.92)
    fig.tight_layout()
    return fig


def nasa_table(ctx: Ctx) -> list[tuple]:
    """(n.º, sol, nombre, lugar, tipo, km desde el aterrizaje) de cada sitio, por orden de sol."""
    rows = []
    for p in sorted(ctx.pois, key=lambda q: first_sol(q) or 10**9):
        d = great_circle_m(ctx.hab[0], ctx.hab[1], p.lat, p.lon) / 1000
        rows.append((p.sol or "—", p.name, p.sample_type, p.rock_type, round(float(d), 1)))
    return rows


# --- 2) cómo lo resolvimos ---------------------------------------------------------------------
def fig_terrain_layers(ctx: Ctx):
    g = ctx.grid
    w, e, s, n = ctx.extent
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    _base_ax(ctx, axes[0], "Paso 1a · Pendiente calculada del DEM real", background="slope")
    _base_ax(ctx, axes[1], "Paso 1b · Mapa de riesgo (umbrales de Perseverance: 10° y 15°)")
    cmap = ListedColormap([C_SAFE, C_RISK, C_BLOCK])
    trav = np.where(g.traversability == 255, np.nan, g.traversability.astype(float))
    axes[1].imshow(trav, extent=(w, e, s, n), cmap=cmap, vmin=0, vmax=2, alpha=0.6, origin="upper")
    from matplotlib.patches import Patch

    axes[1].legend(
        handles=[Patch(color=C_SAFE, label="segura < 10°"), Patch(color=C_RISK, label="riesgo 10°–15°"),
                 Patch(color=C_BLOCK, label="bloqueada > 15°")],
        loc="lower left", fontsize=8, framealpha=0.9,
    )  # fmt: skip
    fig.tight_layout()
    return fig


def terrain_summary(ctx: Ctx) -> dict:
    t = ctx.grid.traversability
    return {
        "celdas": int(t.size),
        "segura_pct": 100 * float((t == 0).mean()),
        "riesgo_pct": 100 * float((t == 1).mean()),
        "bloqueada_pct": 100 * float((t == 2).mean()),
        "pendiente_mediana": float(np.nanmedian(ctx.grid.slope)),
    }


def route_target(ctx: Ctx) -> PointOfInterest:
    """Sitio de muestra más lejano del aterrizaje que sigue dentro del walkback y es alcanzable."""
    cands = sorted(
        (p for p in ctx.pois if first_sol(p)),
        key=lambda p: -great_circle_m(ctx.hab[0], ctx.hab[1], p.lat, p.lon),
    )
    for p in cands:
        if great_circle_m(ctx.hab[0], ctx.hab[1], p.lat, p.lon) > 10_000:
            continue
        try:
            if plan_route(ctx.grid, ctx.hab, (p.lat, p.lon), PRESETS["balanced"]).status == "ok":
                return p
        except RouteError:  # sitio sobre celda bloqueada: se omite
            continue
    raise RuntimeError("ningún sitio alcanzable dentro del walkback")


def route_results(ctx: Ctx, target: PointOfInterest) -> dict:
    return {
        k: plan_route(ctx.grid, ctx.hab, (target.lat, target.lon), PRESETS[k])
        for k in ("safe", "fast")
    }


def fig_routes(ctx: Ctx, target: PointOfInterest, routes: dict):
    """A* vs línea recta vs el recorrido real de Perseverance hasta ese mismo sitio."""
    fig, ax = plt.subplots(figsize=(10, 7.5))
    _base_ax(ctx, ax, f"Paso 2 · Del aterrizaje a «{target.name}»", background="slope", zoom=True)
    ax.plot([ctx.hab[1], target.lon], [ctx.hab[0], target.lat], ":", color="black", lw=2, zorder=4,
            label=f"línea recta: {great_circle_m(ctx.hab[0], ctx.hab[1], target.lat, target.lon) / 1000:.1f} km (cruza pendientes)")  # fmt: skip
    sol = first_sol(target)
    lon, lat = nasa_path_until(ctx, sol)
    real_km = odometer_m(ctx, sol) / 1000
    ax.plot(lon, lat, "-", color="white", lw=3.5, zorder=3, alpha=0.95,
            label=f"Perseverance (recorrido real hasta el sol {sol}): {real_km:.1f} km")  # fmt: skip
    same = abs(routes["safe"].metrics.distance_m - routes["fast"].metrics.distance_m) < 1.0
    for key, color, ls, lw in (("safe", C_SAFE, "-", 3.5), ("fast", C_NASA, "--", 2.5)):
        if key == "fast" and same:
            continue
        r = routes[key]
        pts = np.array([ctx.grid.to_lonlat(*c) for c in r.cells])
        m = r.metrics
        name = "Segura = Rápida (coinciden aquí)" if same else LABELS[key]
        ax.plot(pts[:, 0], pts[:, 1], ls, color=color, lw=lw, zorder=5,
                label=f"nuestro A* · {name}: {m.distance_m / 1000:.1f} km, pend. máx {m.max_slope_deg:.1f}°, "
                      f"{m.pct_risk_cells:.0f}% en riesgo")  # fmt: skip
    ax.plot(target.lon, target.lat, "o", color="white", mec="black", ms=11, zorder=7)
    _mark_habitat(ctx, ax, walkback_m=None)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.94)
    fig.tight_layout()
    return fig


# --- 3) el genético ---------------------------------------------------------------------------
def run_plan(ctx: Ctx, seed: int = 7) -> MissionPlan:
    return plan_missions(ctx.grid, ctx.hab, ctx.pois, [], ctx.cfg, seed=seed)


def fig_pareto(plan: MissionPlan):
    fig, ax = plt.subplots(figsize=(9.5, 6))
    t = [m.metrics.time_h for m in plan.front]
    sci = [m.metrics.science_total for m in plan.front]
    en = [m.metrics.energy_wh for m in plan.front]
    order = np.argsort(t)
    ax.plot(np.array(t)[order], np.array(sci)[order], "-", color="#999", lw=1, zorder=1)
    sc = ax.scatter(t, sci, c=en, cmap="viridis", s=70, ec="black", zorder=3)
    plt.colorbar(sc, ax=ax, label="energía (Wh)")
    all_zero_risk = all(m.metrics.risk_score == 0 for m in plan.front)
    by_id: dict[str, list[str]] = {}
    for name, mid in plan.named.items():
        if name == "safe" and all_zero_risk:
            continue  # sin riesgo en ninguna misión, «segura» sería solo un desempate
        by_id.setdefault(mid, []).append(LABELS[name])
    for mid, names in by_id.items():
        m = plan.mission(mid).metrics
        ax.scatter(
            [m.time_h], [m.science_total], s=260, facecolors="none", ec=C_ACCENT, lw=2.5, zorder=4
        )
        ax.annotate(" / ".join(names), (m.time_h, m.science_total), xytext=(10, -14),
                    textcoords="offset points", fontsize=10, weight="bold", color=C_ACCENT)  # fmt: skip
    ax.set_xlabel("tiempo de misión (h)")
    ax.set_ylabel("ciencia total (suma de valores de los sitios visitados)")
    ax.set_title(f"Paso 3 · El genético propone {len(plan.front)} misiones: cada punto es una forma distinta de repartir el esfuerzo",
                 fontsize=10, loc="left")  # fmt: skip
    ax.margins(x=0.14, y=0.08)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def _draw_mission(ctx: Ctx, plan: MissionPlan, mission, ax, title: str, color=C_OURS):
    _base_ax(ctx, ax, title, zoom=True)
    for leg in plan.legs(mission):
        c = np.array(leg["coordinates"])
        if len(c) >= 2:
            ax.plot(c[:, 0], c[:, 1], "-", color=color, lw=2.5, zorder=4)
    for i, k in enumerate(mission.sequence, start=1):
        p = plan.pois[k - 1]
        ax.scatter([p.lon], [p.lat], s=190, color="white", ec=color, lw=2, zorder=6)
        ax.annotate(
            str(i), (p.lon, p.lat), ha="center", va="center", fontsize=8, weight="bold", zorder=7
        )
    _mark_habitat(ctx, ax)


def fig_missions(ctx: Ctx, plan: MissionPlan):
    names = ["balanced", "science", "fast"]
    fig, axes = plt.subplots(1, 3, figsize=(18, 6.5))
    for ax, name in zip(axes, names, strict=True):
        m = plan.mission(plan.named[name])
        x = m.metrics
        _draw_mission(ctx, plan, m, ax,
                      f"{LABELS[name]}: {len(m.sequence)} parada{'s' if len(m.sequence) != 1 else ''} · ciencia {x.science_total:.1f} · "
                      f"{x.time_h:.0f} h · {x.energy_wh:.0f} Wh")  # fmt: skip
    fig.tight_layout()
    return fig


# --- 4) NASA vs nosotros ----------------------------------------------------------------------
def nasa_vs_ours(ctx: Ctx, plan: MissionPlan) -> dict:
    """Mismo conjunto de paradas (el de nuestra misión científica): orden real de NASA vs el nuestro."""
    ours = plan.mission(plan.named["science"])
    nodes = list(ours.sequence)
    by_node = {k: plan.pois[k - 1] for k in nodes}
    nasa_seq = tuple(
        sorted((k for k in nodes if first_sol(by_node[k])), key=lambda k: first_sol(by_node[k]))
    )
    m_ours = evaluate_sequence(ours.sequence, plan.lm, plan.pois, ctx.cfg)
    m_nasa = evaluate_sequence(nasa_seq, plan.lm, plan.pois, ctx.cfg)
    sols = [first_sol(by_node[k]) for k in nasa_seq]
    legs = []
    prev_node, prev_sol = 0, 0
    for k, sol in zip(nasa_seq, sols, strict=True):
        real = (
            odometer_m(ctx, sol) - odometer_m(ctx, prev_sol) if prev_sol else odometer_m(ctx, sol)
        )
        legs.append({"a": prev_node, "b": k, "sol": sol, "real_m": real,
                     "ours_m": float(plan.lm.distance_m[prev_node, k]), "name": by_node[k].name})  # fmt: skip
        prev_node, prev_sol = k, sol
    return {
        "ours_seq": ours.sequence, "nasa_seq": nasa_seq, "ours": m_ours, "nasa": m_nasa, "legs": legs,
        "nasa_odometer_km": (odometer_m(ctx, sols[-1]) - odometer_m(ctx, sols[0])) / 1000 if sols else 0.0,
        "sol_first": sols[0] if sols else None, "sol_last": sols[-1] if sols else None,
    }  # fmt: skip


def _draw_sequence(ctx, plan, seq, ax, title, color):
    _base_ax(ctx, ax, title, zoom=True)
    nodes = (0, *seq, 0)
    for a, b in zip(nodes[:-1], nodes[1:], strict=True):
        c = np.array([ctx.grid.to_lonlat(*rc) for rc in plan.lm.paths[(a, b)]])
        if len(c) >= 2:
            ax.plot(c[:, 0], c[:, 1], "-", color=color, lw=2.2, zorder=4)
    for i, k in enumerate(seq, start=1):
        p = plan.pois[k - 1]
        ax.scatter([p.lon], [p.lat], s=170, color="white", ec=color, lw=2, zorder=6)
        ax.annotate(
            str(i), (p.lon, p.lat), ha="center", va="center", fontsize=7, weight="bold", zorder=7
        )
    _mark_habitat(ctx, ax)


def fig_nasa_vs_ours(ctx: Ctx, plan: MissionPlan, cmp: dict):
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    _draw_sequence(ctx, plan, cmp["nasa_seq"], axes[0],
                   f"NASA: orden real de las muestras · {cmp['nasa'].distance_m / 1000:.1f} km, "
                   f"{cmp['nasa'].time_h:.0f} h", C_NASA)  # fmt: skip
    lon, lat = nasa_path_until(ctx, cmp["sol_last"])
    axes[0].plot(lon, lat, "-", color="white", lw=1.2, alpha=0.9, zorder=3)
    axes[0].annotate("línea blanca: recorrido real de Perseverance", (0.02, 0.02), xycoords="axes fraction",
                     color="white", fontsize=8, weight="bold")  # fmt: skip
    _draw_sequence(ctx, plan, cmp["ours_seq"], axes[1],
                   f"Nosotros: orden optimizado · {cmp['ours'].distance_m / 1000:.1f} km, "
                   f"{cmp['ours'].time_h:.0f} h", C_OURS)  # fmt: skip
    fig.tight_layout()
    return fig


def fig_legs(cmp: dict):
    legs = cmp["legs"]
    fig, ax = plt.subplots(figsize=(13, 5))
    x = np.arange(len(legs))
    ax.bar(
        x - 0.2,
        [leg["real_m"] / 1000 for leg in legs],
        0.4,
        color=C_NASA,
        label="Perseverance (odómetro real)",
    )
    ax.bar(
        x + 0.2,
        [leg["ours_m"] / 1000 for leg in legs],
        0.4,
        color=C_OURS,
        label="nuestro A* (mismo tramo)",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{leg['name'].split(' (')[0][:16]}\nsol {leg['sol']}" for leg in legs],
        rotation=60,
        ha="right",
        fontsize=7,
    )
    ax.set_ylabel("km entre una muestra y la siguiente")
    ax.set_title("Distancia entre muestras consecutivas: lo que condujo NASA vs la ruta más barata de nuestro modelo",
                 fontsize=10, loc="left")  # fmt: skip
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


# --- 5) pruebas visibles ------------------------------------------------------------------------
def check_astar_vs_dijkstra(ctx: Ctx, n: int = 10, seed: int = 3):
    cm = build_costmap(ctx.grid, PRESETS["balanced"])
    rr, cc = np.nonzero(~cm.blocked)
    free = list(zip(rr.tolist(), cc.tolist(), strict=True))
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        a, b = (free[i] for i in rng.choice(len(free), 2, replace=False))
        ra, rd = astar(cm, a, b), dijkstra(cm, a, b)
        out.append((ra.cost, rd.cost, ra.expanded, rd.expanded))
    return out


def check_ga_vs_bruteforce(ctx: Ctx, budgets=(6000.0, 9000.0)):
    pois = [p for p in ctx.pois if great_circle_m(ctx.hab[0], ctx.hab[1], p.lat, p.lon) <= 10_000]
    subset = pois[1::2][:8]
    rows = []
    for budget in budgets:
        p = plan_missions(ctx.grid, ctx.hab, subset, [], ctx.cfg, energy_budget_wh=budget, seed=7)
        _, best = best_science(p.lm, p.pois, ctx.cfg, budget, p.max_time_h)
        rows.append((budget, p.mission(p.named["science"]).metrics.science_total, best))
    return rows
