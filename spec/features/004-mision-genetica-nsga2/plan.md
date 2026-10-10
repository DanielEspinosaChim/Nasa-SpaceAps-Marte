# Plan — 004 Misión genética (NSGA-II)

## Enfoque técnico

El problema es un **orienteering con varios objetivos**: elegir un
subconjunto de POI y su orden, saliendo del hábitat y volviendo a él, bajo
un presupuesto. Se resuelve en dos etapas.

**Etapa 1. Matriz de tramos (exacta, sin genético).** Se construye el mapa
de costos de la 003 con el preset `balanced`, sumando las restricciones
duras (bloqueo, zonas prohibidas y radio de walkback). El mapa se convierte
en un grafo disperso de 8 vecinos (`scipy.sparse.csr_matrix`, donde el peso
de la arista a→b es `costo(a→b)` de la 003). Después se corre
`scipy.sparse.csgraph.dijkstra(indices=[hábitat, POI…],
return_predecessors=True)`: N+1 búsquedas de una sola fuente en C, en vez de
(N+1)² llamadas a A\*. Con los predecesores se reconstruye cada tramo y se
calculan sus métricas con `metrics.py` de la 003, añadiendo `energy_wh` y
`risk_m` (metros recorridos sobre celdas con transitabilidad `1`).

**Etapa 2. Genético multiobjetivo (pymoo NSGA-II).**

- **Codificación por claves aleatorias** (*random keys*): un vector de N
  reales en [0,1], uno por POI. Un POI se visita si su clave es ≥ 0.5, y
  los visitados se ordenan por clave descendente. Así se usan los operadores
  estándar de pymoo para reales (SBX y mutación polinómica) sin operadores
  de permutación propios, y toda solución decodifica a una misión válida en
  estructura.
- **Mejora local del orden**: después de decodificar, se aplica 2-opt al
  orden de los visitados para minimizar el tiempo. Es barato (N ≤ 20) y
  evita que el genético gaste generaciones en ordenar.
- **Objetivos** (pymoo minimiza los tres):
  - `f1 = −science_total`, la suma de `science_value` de los POI visitados.
  - `f2 = time_h`, el tiempo de los tramos más el `dwell_time_h` de cada
    POI.
  - `f3 = risk_m`, los metros en terreno de riesgo más una penalización por
    pendiente máxima: `risk_m + 50 · max(0, max_slope_deg − 10)`.
- **Restricciones** (pymoo `G ≤ 0`):
  - `g1 = energy_wh − energy_budget_wh`
  - `g2 = time_h − max_time_h`
  - `g3 =` número de tramos sin camino (infinito en la matriz)
- **Parámetros por defecto**: población de 100, 200 generaciones,
  `eliminate_duplicates=True` y semilla configurable.

**Modelo de energía** (simple y documentado):

```
energy_wh(tramo) = e_per_m · distance_m + e_per_m_up · elevation_gain_m
energy_wh(misión) = Σ tramos + Σ_POI (p_dwell_w · dwell_time_h)
```

Valores por defecto en `mission_config.yaml`: `e_per_m = 0.25 Wh/m`,
`e_per_m_up = 2.0 Wh/m`, `p_dwell_w = 60 W` y
`energy_budget_wh = 12000 Wh`. Son valores de un rover genérico de demo, no
de Perseverance. La ficha de la misión lo dice en `limitations`.
El validador científico revisa estos órdenes de magnitud antes de la
demo; se cambian en el YAML sin tocar código.

**Misiones con nombre y selector.** Los objetivos del frente se normalizan
a [0,1] con min-max dentro del frente. `safe`, `fast` y `science` son
extremos por un solo objetivo. `balanced` es la de menor distancia
euclidiana al punto ideal (0,0,0). El selector de la 005 usa la misma
normalización:

```
score(m) = w_science · f1n(m) + w_speed · f2n(m) + w_safety · f3n(m)
```

y devuelve la misión con menor `score`. Los empates se resuelven por
`mission_id`, para que el resultado sea determinista.

**Explicaciones** (plantillas del servidor, con cifras):

- *Visitado*: ciencia del POI y ahorro del orden elegido frente al
  alternativo más cercano (con 2-opt se conoce el delta).
- *Descartado en la optimización*: energía o tiempo extra que costaría
  insertarlo en la mejor posición frente a su ciencia, y qué restricción
  rompería.
- *Descartado antes de optimizar*: `reason_code` con su distancia al
  hábitat o el nombre de la zona prohibida.

**Baselines para los tests:**

- `bruteforce.py`: enumera todas las combinaciones y órdenes para N ≤ 8.
- `greedy.py`: inserción voraz por ciencia/costo, que genera una misión
  por cada presupuesto en una rejilla de 10 presupuestos.
- Hipervolumen con `pymoo.indicators.hv.HV`, con un punto de referencia
  fijo derivado de los máximos.

## Archivos a crear/modificar

- `pyproject.toml`: agregar `pymoo`.
- `src/marsmap/config/mission_config.yaml`: modelo de energía, presupuesto,
  tiempo máximo, radio de walkback (10 000 m) y parámetros del genético.
- `src/marsmap/planning/mission/__init__.py`
- `src/marsmap/planning/mission/poi.py`: modelo `PointOfInterest` y carga y
  validación de `poi.geojson`.
- `src/marsmap/planning/mission/legs.py`: `build_leg_matrix(costmap, habitat, pois)`
  → `LegMatrix` (grafo disperso, Dijkstra multi-fuente y reconstrucción).
- `src/marsmap/planning/mission/energy.py`: modelo de energía.
- `src/marsmap/planning/mission/prefilter.py`: descartes previos con su
  `reason_code`.
- `src/marsmap/planning/mission/encoding.py`: decodificación de claves
  aleatorias a secuencia, y 2-opt.
- `src/marsmap/planning/mission/problem.py`: `MissionProblem(pymoo.Problem)`
  con objetivos y restricciones vectorizados.
- `src/marsmap/planning/mission/optimize.py`: `plan_mission(...)` →
  `MissionResult` (corre NSGA-II, filtra no dominados y quita duplicados).
- `src/marsmap/planning/mission/select.py`: misiones con nombre y
  `select_mission(front, weights)`.
- `src/marsmap/planning/mission/explain.py`: explicaciones de visitados y
  descartados.
- `src/marsmap/planning/mission/baselines/bruteforce.py`
- `src/marsmap/planning/mission/baselines/greedy.py`
- `src/marsmap/terrain/synthetic.py`: agregar `generate_pois(bbox, n, seed)`
  para tests y para la demo offline.
- `src/marsmap/api/routers/missions.py`: endpoints de misión.
- `src/marsmap/api/schemas.py`: agregar `MissionRequest`, `MissionOut`,
  `MissionResultOut` y `SelectRequest`.
- `data/processed/jezero/poi.geojson`: ampliar el provisional de la 003
  con `science_value`, `dwell_time_h`, `category`, `rationale` y
  `source`.
- `tests/planning/mission/test_legs.py`
- `tests/planning/mission/test_encoding.py`
- `tests/planning/mission/test_prefilter.py`
- `tests/planning/mission/test_optimize.py`
- `tests/planning/mission/test_select.py`
- `tests/planning/mission/test_explain.py`
- `tests/planning/mission/test_quality.py` (contra fuerza bruta y greedy)
- `tests/api/test_missions.py`
- `frontend/src/missionPlanner.js`: botón "Planificar misión", llamada a la
  API y botones de las misiones con nombre.
- `frontend/src/missionLayer.js`: tramos coloreados por riesgo y
  marcadores numerados.
- `frontend/src/missionReport.js`: métricas, explicaciones y descartes con
  `textContent`.
- `frontend/e2e/mission.spec.js`

## Endpoints

| Método | Path | Descripción |
|---|---|---|
| GET | `/api/regions/{region_id}/pois` | Lista los POI de la región como GeoJSON, con `science_value` y `rationale` |
| POST | `/api/regions/{region_id}/missions` | Calcula el frente de Pareto y las misiones con nombre |
| POST | `/api/regions/{region_id}/missions/{result_id}/select` | Devuelve la misión del frente que mejor encaja con los pesos (usada por la 005) |

## Modelo de datos

**`PointOfInterest`** (cada feature de `poi.geojson`)

| Campo | Tipo | Notas |
|---|---|---|
| poi_id | str | `^[a-z0-9_]+$`, único en la región |
| name | str | legible |
| lat, lon | float | geometría Point, lon −180..180 E |
| science_value | float | [0, 1] |
| dwell_time_h | float | [0, 12], tiempo de estudio en el sitio |
| category | str | por ejemplo `delta`, `crater_rim`, `outcrop`, `dune` |
| rationale | str | por qué tiene ese valor científico |
| source | str | referencia (por ejemplo una nota de Mars 2020) o `synthetic` |

**`MissionRequest`**

| Campo | Tipo | Notas |
|---|---|---|
| habitat | {lat, lon} | requerido, dentro del bbox y en una celda no bloqueada |
| poi_ids | list[str] \| null | null = todos los de la región; máximo 20 |
| energy_budget_wh | float | (0, 50 000]; por defecto 12 000 |
| max_time_h | float | (0, 720]; por defecto 240 (a 100 m/h, 10 km de walkback son ~100 h por tramo) |
| max_radius_m | float | (0, 100 000]; por defecto 10 000 (walkback) |
| use_forbidden_zones | bool | por defecto true |
| seed | int | [0, 2³¹), por defecto 42 |
| pop_size | int | [20, 200], por defecto 100 |
| n_generations | int | [10, 300], por defecto 200 |

**`MissionOut`** (una misión del frente)

| Campo | Tipo | Notas |
|---|---|---|
| mission_id | str | estable dentro del resultado (`m00`, `m01`…), ordenado por ciencia descendente |
| sequence | list[str] | `poi_id` en orden, sin el hábitat |
| geometry | GeoJSON LineString | hábitat → POI… → hábitat |
| legs | list[{from, to, distance_m, time_h, energy_wh, risk_m, max_slope_deg}] | |
| science_total | float | |
| time_h | float | tramos más estancias |
| energy_wh | float | |
| risk_m | float | metros en terreno de riesgo |
| risk_score | float | tercer objetivo: `risk_m` + penalización por pendiente máxima |
| distance_m | float | |
| max_slope_deg | float | |
| explanations | list[str] | ≥ 1 por POI visitado y descartado |

**`MissionResultOut`**

| Campo | Tipo | Notas |
|---|---|---|
| result_id | str | hash de los parámetros, para la caché y `select` |
| front | list[MissionOut] | ≤ `max_front_size` |
| named | {safe, fast, science, balanced: str} | `mission_id` de cada una |
| discarded | list[{poi_id, reason_code, reason}] | descartes previos |
| params_used | MissionRequest | con los valores por defecto aplicados |
| limitations | list[str] | por ejemplo "modelo de energía genérico, no de Perseverance" |
| compute_ms | int | |

**`SelectRequest`**: `{safety, science, speed: float}`, cada uno en
[0, 1], con al menos uno > 0. Responde con `MissionOut`.

## Flujo técnico paso a paso

1. Pydantic valida el `MissionRequest`, se resuelve la región y se aplica
   el rate limit (el mismo módulo de la 003, con un límite más bajo).
2. Se calcula `result_id`. Si está en la caché LRU, se devuelve directo.
3. Se cargan los POI y se aplica el `prefilter` (walkback, zonas
   prohibidas). Los excluidos van a `discarded`.
4. Se construye el mapa de costos `balanced` con las restricciones y se
   calcula la `LegMatrix`. Los POI sin camino desde el hábitat van a
   `discarded` como `unreachable`.
5. Si no queda ningún POI, se devuelve un frente con la misión vacía
   (quedarse en el hábitat) y una explicación.
6. Se corre NSGA-II con timeout (30 s), se decodifica la población final,
   se filtran los no dominados y se quitan las secuencias duplicadas. Si
   el frente supera `max_front_size`, se recorta por crowding distance.
7. Se calculan las misiones con nombre, la geometría de cada misión
   (concatenando los tramos) y las explicaciones.
8. `select` busca el `result_id` en la caché (404 `result_expired` si ya
   no está) y aplica `select_mission`.
9. El frontend dibuja `balanced`, permite cambiar entre las misiones con
   nombre y lista los descartes.

## Consideraciones de seguridad específicas de esta feature

- **Abuso de cómputo**: es el endpoint más caro del proyecto. Tiene rate
  limit propio (por ejemplo 5/min por IP), timeout duro de 30 s, y topes en
  `pop_size`, `n_generations` y el número de POI.
- La caché de resultados es LRU con tamaño máximo. `result_id` es un hash
  de los parámetros validados y nunca se usa para construir rutas de
  archivo.
- `poi_ids` se valida con regex y contra los POI de la región.
- Las explicaciones salen de plantillas del servidor y se pintan con
  `textContent` (los `name` y `rationale` de los POI también).
