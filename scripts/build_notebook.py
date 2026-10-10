"""Genera y ejecuta notebooks/Mars_Scout_demo.ipynb (+ versión HTML autocontenida).

    python scripts/build_notebook.py

Requiere los datos reales: data/raw/jezero/dem.tif y data/raw/jezero/mars2020/ (ver data/README.md).
El notebook queda ya ejecutado, con todos los gráficos incluidos: se puede abrir sin correr nada.
"""

from pathlib import Path

import nbformat as nbf
from nbconvert import HTMLExporter
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip("\n"))


def code(text: str):
    return nbf.v4.new_code_cell(text.strip("\n"))


CELLS = [
    md("""
# Mars Scout · cómo lo hizo NASA en Marte y cómo lo resolvimos nosotros

**Qué es esto.** Un rover simulado recibe el mapa real de Marte y tiene que decidir **qué lugares
visitar, en qué orden y por dónde ir**, sin quedarse sin energía y sin meterse en terreno peligroso.
Aquí lo comparamos con lo que **de verdad hizo Perseverance** en el cráter Jezero.

**Cómo usarlo.** No necesitas entender el código: cada sección tiene una explicación en texto y un
gráfico. Si quieres volver a ejecutarlo, usa *Ejecutar todo* (*Run All*). Dura unos 30 segundos.

> Todo lo que ves usa **datos reales** (ver sección 1). No hay terreno inventado en este documento.
"""),
    code("""
%matplotlib inline
import matplotlib.pyplot as plt
plt.rcParams.update({"figure.dpi": 90, "axes.titlesize": 11})

from marsmap import notebook_tools as nt

ctx = nt.load_context()
print(f"Terreno real cargado: {ctx.grid.shape[1]} x {ctx.grid.shape[0]} celdas de 200 m")
print(f"Sitios de muestras reales de Perseverance: {len(ctx.pois)}")
print(f"Waypoints reales del rover: {len(ctx.wp_sol)}  (sol {int(ctx.wp_sol.min())} a {int(ctx.wp_sol.max())})")
print(f"Sitio de aterrizaje (dato de NASA): {ctx.hab[0]:.5f} N, {ctx.hab[1]:.5f} E")
"""),
    md("""
## 1. Los datos

| Qué | De dónde | ¿NASA? |
|---|---|---|
| **Relieve de Marte** (mapa de alturas, 200 m por celda) | MOLA–HRSC, publicado por USGS | **Parcial**: MOLA es de NASA (sonda MGS); HRSC es de la ESA (Mars Express) |
| **Sitios donde Perseverance tomó muestras** (22) | NASA/JPL, capa *Sampling Locations* | Sí |
| **Recorrido real del rover** (703 posiciones) y **aterrizaje** | NASA/JPL, capa *Rover Waypoints* | Sí |

Lo que **no** es un dato de NASA y es criterio nuestro: el *valor científico* de cada sitio (una regla
que da más puntos a la roca sedimentaria y a la que muestra alteración por agua), y los consumos de
energía y velocidades del rover, que son supuestos genéricos de demostración.
"""),
    code("fig = nt.fig_nasa_overview(ctx); plt.show()"),
    md("""
**Cómo leer el gráfico de la derecha.** La línea blanca es el camino **real** que recorrió Perseverance
desde que aterrizó (la estrella). Los puntos de colores son los sitios donde tomó muestras: más
oscuro = antes en la misión (sol = día marciano), más claro = después. La línea azul punteada es el
límite de **10 km** desde el aterrizaje (el «walkback»: hasta dónde se puede ir y poder volver).
"""),
    md("""
## 2. Lo que hizo NASA

Perseverance tomó muestras en este orden (los sitios fuera de los 10 km son los del borde del cráter):
"""),
    code("""
print(f"{'sol':>10}  {'sitio':<48}{'tipo':<12}{'km':>5}")
print("-" * 78)
for sol, name, stype, rock, km in nt.nasa_table(ctx):
    flag = "  (fuera del walkback)" if km > 10 else ""
    print(f"{sol:>10}  {name[:46]:<48}{stype[:10]:<12}{km:>5.1f}{flag}")
"""),
    md("""
## 3. Cómo lo resolvimos nosotros

Lo hacemos en tres pasos. Cada uno resuelve un problema distinto.

### Paso 1 · Dónde se puede ir: el mapa de riesgo
Del mapa de alturas calculamos la **pendiente** de cada celda y la clasificamos con los umbrales que se
usan con Perseverance: menos de 10° es segura, de 10° a 15° tiene riesgo y más de 15° está bloqueada.
"""),
    code("""
fig = nt.fig_terrain_layers(ctx); plt.show()
s = nt.terrain_summary(ctx)
print(f"Segura: {s['segura_pct']:.1f}%   Riesgo: {s['riesgo_pct']:.1f}%   Bloqueada: {s['bloqueada_pct']:.1f}%   "
      f"(pendiente mediana {s['pendiente_mediana']:.1f}°)")
"""),
    md("""
### Paso 2 · Por dónde ir: rutas óptimas (algoritmo A*)
Entre dos puntos, A* encuentra el **camino más barato** (no el más corto: penaliza pendientes y terreno
de riesgo). Es un algoritmo exacto: garantiza que no existe uno mejor. Aquí, del aterrizaje al sitio más
lejano que aún queda dentro de los 10 km.
"""),
    code("""
target = nt.route_target(ctx)
routes = nt.route_results(ctx, target)
fig = nt.fig_routes(ctx, target, routes); plt.show()
print("Por qué eligió esta ruta (explicación generada por el sistema):")
for line in routes["safe"].explanations:
    print("  -", line)
"""),
    md("""
**Cómo leer el gráfico.** El fondo muestra la pendiente (rojo oscuro = muy empinado). La línea
punteada negra es la recta, que cruza terreno difícil. La línea verde es la ruta de A*, que **rodea lo
empinado** a cambio de unos cientos de metros más. La línea blanca gruesa es el recorrido **real** de
Perseverance *acumulado hasta ese sol*: incluye todo lo que hizo antes, no solo ir hasta ese sitio.

> Las rutas se ven «en escalera» porque el mapa es una cuadrícula de 200 m y solo permitimos 8
> direcciones. Es una limitación de la versión actual, no del algoritmo.
"""),
    md("""
### Paso 3 · Qué visitar y en qué orden: el algoritmo genético
Aquí está el problema difícil. Hay 17 sitios dentro del alcance, y elegir **cuáles** visitar y **en qué
orden** con energía y tiempo limitados tiene millones de combinaciones (es un problema clásico llamado
*orienteering*). A* no puede resolverlo; un **algoritmo genético** sí puede explorar bien las opciones.

No devuelve una sola respuesta, sino **un abanico de misiones**: cada punto del gráfico es una misión
distinta, con su equilibrio entre ciencia, tiempo y energía.
"""),
    code("""
plan = nt.run_plan(ctx)
print(f"El genético encontró {len(plan.front)} misiones distintas en {plan.compute_ms / 1000:.1f} s")
print(f"Sitios considerados: {len(plan.pois)}  ·  descartados por quedar a más de 10 km: {len(plan.discarded)}")
for d in plan.discarded:
    print("  -", d.reason)
fig = nt.fig_pareto(plan); plt.show()
"""),
    md("""
**Cómo leer el gráfico.** Cuanto más a la derecha, más tiempo; cuanto más arriba, más ciencia. No hay
una «mejor» misión: hay un **compromiso**. La *Rápida* va a un solo sitio. La *Científica* visita casi
todo. La *Balanceada* es el punto de equilibrio. Quien planifica elige según su prioridad (en la
aplicación web esto se hace con controles deslizantes).

> En este terreno **ninguna misión cruza zonas de riesgo** (el suelo del cráter es mayormente llano
> y A* las rodea), por eso no mostramos una misión «Segura»: sería solo un desempate arbitrario.
"""),
    code("fig = nt.fig_missions(ctx, plan); plt.show()"),
    code("""
mission = plan.mission(plan.named["balanced"])
print("La misión Balanceada, explicada (primeras líneas):")
for line in plan.explanations[mission.mission_id][:5]:
    print("  -", line)
"""),
    md("""
## 4. Comparación: NASA vs nosotros

La pregunta justa: **para visitar los mismos sitios, ¿qué orden gasta menos?** Tomamos las 16 paradas de
nuestra misión científica y comparamos dos órdenes, midiendo los dos con el **mismo modelo de terreno**:

- el orden **real** en que NASA tomó esas muestras (por fecha), y
- el orden que **nosotros** calculamos.
"""),
    code("""
cmp = nt.nasa_vs_ours(ctx, plan)
n, o = cmp["nasa"], cmp["ours"]
print(f"Mismo conjunto de {len(cmp['ours_seq'])} paradas, ida y vuelta al aterrizaje:\\n")
print(f"{'':<28}{'distancia':>12}{'tiempo':>10}{'energía':>12}")
print(f"{'Orden real de NASA':<28}{n.distance_m / 1000:>9.1f} km{n.time_h:>7.0f} h{n.energy_wh:>9.0f} Wh")
print(f"{'Nuestro orden':<28}{o.distance_m / 1000:>9.1f} km{o.time_h:>7.0f} h{o.energy_wh:>9.0f} Wh")
print(f"{'Ahorro':<28}{100 * (1 - o.distance_m / n.distance_m):>10.0f} %{100 * (1 - o.time_h / n.time_h):>8.0f} %{100 * (1 - o.energy_wh / n.energy_wh):>10.0f} %")
print(f"\\nContexto real: entre la muestra del sol {cmp['sol_first']} y la del sol {cmp['sol_last']}, el odómetro de")
print(f"Perseverance avanzó {cmp['nasa_odometer_km']:.1f} km (incluye desvíos, exploración y maniobras).")
fig = nt.fig_nasa_vs_ours(ctx, plan, cmp); plt.show()
"""),
    code("fig = nt.fig_legs(cmp); plt.show()"),
    md("""
**Lo que sí dice esta comparación:** con el mismo modelo, conocer **todos los objetivos desde el
principio** permite un orden más corto. Es justo lo que hace un planificador, y NASA no podía hacerlo
así porque los objetivos fueron apareciendo durante años.

**Lo que NO dice, y hay que ser honestos:**
- **No dice que NASA lo hiciera mal.** Su orden respondió a las fases de la misión, a objetivos que
  fueron surgiendo y a la seguridad del rover, no a minimizar distancia.
- Las distancias de NASA en el gráfico de barras son del **odómetro**: incluyen desvíos, así que no son
  comparables punto a punto con nuestra ruta más barata. Sirven como contexto, no como medida exacta.
- Nuestro modelo **no ve los peligros que el satélite no muestra** (arena blanda, rocas pequeñas), y
  NASA sí los enfrenta. Esa parte todavía no está construida.
- Falta comparar también nuestras **rutas** con el recorrido real tramo a tramo.
"""),
    md("""
## 5. Pruebas de que el algoritmo funciona

Dos comprobaciones, con datos reales, que se ejecutan aquí mismo:
"""),
    code("""
res = nt.check_astar_vs_dijkstra(ctx, n=10)
ok = all(abs(a - b) < 1e-6 for a, b, _, _ in res)
print("A* contra Dijkstra (método exhaustivo), 10 pares de puntos al azar sobre terreno real:")
print(f"  {'✓' if ok else '✗'} mismo costo en {sum(abs(a - b) < 1e-6 for a, b, _, _ in res)}/10 casos")
print(f"  A* exploró {sum(r[2] for r in res):,} celdas; Dijkstra {sum(r[3] for r in res):,} "
      f"({sum(r[3] for r in res) / sum(r[2] for r in res):.1f}x más)\\n")
print("Genético contra fuerza bruta (probar TODOS los órdenes) con 8 sitios reales:")
for budget, ga, exact in nt.check_ga_vs_bruteforce(ctx):
    mark = "✓" if abs(ga - exact) < 1e-6 else "✗"
    print(f"  {mark} presupuesto {budget:,.0f} Wh: genético {ga:.2f}  ·  óptimo exacto {exact:.2f}")
"""),
    md("""
## 6. Qué demuestra este trabajo y qué no

**Demuestra:**
1. Con datos reales de NASA, el sistema produce misiones **válidas**: no pasan por terreno bloqueado y
   respetan energía, tiempo y el límite de 10 km.
2. A* es **exacto** y el genético **encuentra el óptimo** donde se puede comprobar (8 sitios).
3. Para el mismo conjunto de sitios, un orden planificado es **más corto** que el orden histórico.

**No demuestra todavía:**
1. Que nuestro modelo de costos refleje la realidad: los umbrales y pesos son los de la literatura, sin
   calibrar contra los datos de conducción reales.
2. Nada sobre **peligros ocultos** (lo que el satélite no ve): es la siguiente etapa.
3. El **valor científico** de cada sitio es una regla nuestra, no una valoración de NASA.
4. La energía y velocidad del rover son **supuestos genéricos**, no los de Perseverance.

*Fuentes de datos: DEM MOLA–HRSC (NASA/ESA, vía USGS) y capas públicas de Mars 2020 (NASA/JPL, mars.nasa.gov).*
"""),
]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    nb = nbf.v4.new_notebook()
    nb.cells = CELLS
    nb.metadata["kernelspec"] = {
        "name": "marsmap",
        "display_name": "Mars Scout (.venv)",
        "language": "python",
    }
    ExecutePreprocessor(timeout=600, kernel_name="marsmap").preprocess(
        nb, {"metadata": {"path": str(ROOT)}}
    )
    ipynb = OUT / "Mars_Scout_demo.ipynb"
    nbf.write(nb, ipynb)
    body, _ = HTMLExporter().from_notebook_node(nb)
    (OUT / "Mars_Scout_demo.html").write_text(body, encoding="utf-8")
    print(f"listo: {ipynb} ({ipynb.stat().st_size // 1024} KB) y {OUT / 'Mars_Scout_demo.html'}")


if __name__ == "__main__":
    main()
