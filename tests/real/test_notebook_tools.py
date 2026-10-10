"""Prueba de humo del notebook: las funciones de gráficos y comparación corren con datos reales."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

from marsmap import notebook_tools as nt  # noqa: E402
from tests.real.test_jezero_real import DEM  # noqa: E402

pytestmark = [
    pytest.mark.real,
    pytest.mark.skipif(not DEM.is_file(), reason="falta data/raw/jezero/dem.tif"),
]


@pytest.fixture(scope="module")
def ctx():
    try:
        return nt.load_context()
    except FileNotFoundError as exc:
        pytest.skip(str(exc))


@pytest.fixture(scope="module")
def plan(ctx):
    return nt.run_plan(ctx)


def test_context_uses_nasa_landing_and_waypoints(ctx):
    assert ctx.hab == pytest.approx((18.44462715, 77.45088572))
    assert len(ctx.wp_sol) >= 700 and ctx.wp_sol[0] == 13
    assert ctx.wp_odo_m[-1] > 20_000  # el rover recorrió decenas de km
    w, e, s, n = ctx.zoom
    assert w < ctx.hab[1] < e and s < ctx.hab[0] < n


def test_odometer_is_monotonic(ctx):
    vals = [nt.odometer_m(ctx, sol) for sol in (13, 164, 500, 1000, 1980)]
    assert vals == sorted(vals) and vals[0] == 0.0


def test_all_figures_render(ctx, plan):
    target = nt.route_target(ctx)
    routes = nt.route_results(ctx, target)
    cmp = nt.nasa_vs_ours(ctx, plan)
    figs = [
        nt.fig_nasa_overview(ctx),
        nt.fig_terrain_layers(ctx),
        nt.fig_routes(ctx, target, routes),
        nt.fig_pareto(plan),
        nt.fig_missions(ctx, plan),
        nt.fig_nasa_vs_ours(ctx, plan, cmp),
        nt.fig_legs(cmp),
    ]
    assert all(f.axes for f in figs)
    plt.close("all")


def test_comparison_uses_same_stops_and_real_sols(ctx, plan):
    cmp = nt.nasa_vs_ours(ctx, plan)
    assert set(cmp["ours_seq"]) == set(cmp["nasa_seq"])  # mismo conjunto de paradas
    sols = [leg["sol"] for leg in cmp["legs"]]
    assert sols == sorted(sols)  # el orden de NASA es cronológico
    assert cmp["ours"].distance_m > 0 and cmp["nasa"].distance_m > 0
    assert cmp["nasa_odometer_km"] > 0


def test_nasa_table_covers_all_sites(ctx):
    rows = nt.nasa_table(ctx)
    assert len(rows) == len(ctx.pois) and any(r[4] > 10 for r in rows)
