# Plan — 003 Planificador A\*

## Enfoque técnico

Se usa una cuadrícula de 8 vecinos sobre las celdas del raster. El costo de
moverse de la celda *a* a la *b* es:

```
costo(a→b) = d3D(a,b) · (1 + w_slope·s(b) + w_rough·r(b) + w_risk·[trav(b)==1])
```

donde `d3D` es la distancia horizontal en metros (corregida por latitud)
combinada con el desnivel, `s` es la pendiente normalizada a [0,1] con
15° = 1 y `r` es la rugosidad normalizada por percentil 95. Las celdas
bloqueadas tienen costo infinito y no se expanden. La heurística es la
distancia 3D en línea recta multiplicada por el multiplicador mínimo
(1.0), lo que la hace admisible y garantiza la optimalidad. Las zonas
prohibidas (GeoJSON con búfer en metros) y el radio máximo desde el hábitat
se rasterizan a una máscara booleana que se suma a las celdas bloqueadas.
Las explicaciones salen de comparar la ruta con la línea recta: qué celdas
de alto costo o bloqueadas atraviesa la recta y cuánto desvío añade la
ruta.

**Presets de pesos** (provisionales y ajustables):

| Preset | w_slope | w_rough | w_risk | w_science |
|---|---|---|---|---|
| safe | 4.0 | 2.0 | 6.0 | 0.0 |
| fast | 0.5 | 0.2 | 1.0 | 0.0 |
| science | 1.5 | 0.8 | 3.0 | 1.0 |
| balanced | 2.0 | 1.0 | 3.0 | 0.0 |

Son valores iniciales. Viven en `presets.py` y se recalibran con la
tarea "Calibrar presets con el DEM real de Jezero" sin cambiar la spec.

El preset `science` reduce el costo de las celdas dentro de un radio de los
puntos de interés: `costo × (1 − 0.5·w_science·interés(b))`, con un mínimo
de 0.5 para no romper la admisibilidad. La heurística usa ese mínimo.

**Velocidad estimada** del rover para `est_time_h`: 100 m/h en terreno
seguro y 50 m/h en terreno de riesgo.
Son valores conservadores de demo y se declaran en `limitations`.

## Archivos a crear/modificar

- `src/marsmap/planning/costmap.py`: `build_costmap(layers, weights, constraints)`
  → costos por celda y máscara de bloqueo.
- `src/marsmap/planning/constraints.py`: rasterización de zonas prohibidas
  con búfer y del radio desde el hábitat.
- `src/marsmap/planning/astar.py`: `astar(costmap, start, goal)` con
  `heapq` y 8 vecinos.
- `src/marsmap/planning/dijkstra.py`: implementación de referencia para los
  tests de optimalidad (y para el baseline de la 010).
- `src/marsmap/planning/metrics.py`: distancia, tortuosidad, pendientes,
  desnivel, perfil y tiempo estimado.
- `src/marsmap/planning/explain.py`: generación de explicaciones con
  cifras.
- `src/marsmap/planning/presets.py`: presets de pesos.
- `src/marsmap/api/routers/routes.py`: endpoint `POST /route`.
- `src/marsmap/api/schemas.py`: agregar `RouteRequest` y `RouteOut`.
- `src/marsmap/api/ratelimit.py`: límite por IP y timeout para endpoints de
  cómputo.
- `data/processed/jezero/forbidden_zones.geojson`: vacío por defecto, con
  un ejemplo comentado en `data/README.md`.
- `data/processed/jezero/poi.geojson`: puntos de interés provisionales
  (por ejemplo el delta occidental y el sitio de aterrizaje Octavia E.
  Butler). Cada punto lleva su `source`; los que no tengan fuente
  verificada se marcan `source: "aproximado"` y la UI lo muestra.
- `tests/planning/test_astar.py`
- `tests/planning/test_constraints.py`
- `tests/planning/test_metrics.py`
- `tests/planning/test_explain.py`
- `tests/api/test_routes.py`
- `frontend/src/routePlanner.js`: selección de inicio y destino, presets y
  dibujo de la ruta.
- `frontend/src/profileChart.js`: perfil altimétrico en `<canvas>`.
- `frontend/src/routeReport.js`: métricas y explicaciones con
  `textContent`.
- `frontend/e2e/route.spec.js`

## Endpoints

| Método | Path | Descripción |
|---|---|---|
| POST | `/api/regions/{region_id}/route` | Calcula la ruta A\* entre dos puntos con preset o pesos explícitos |
| GET | `/api/regions/{region_id}/route/presets` | Lista los presets de pesos disponibles |

## Modelo de datos

**`RouteRequest`**

| Campo | Tipo | Notas |
|---|---|---|
| start | {lat: float, lon: float} | requerido, dentro del bbox |
| goal | {lat: float, lon: float} | requerido, dentro del bbox |
| preset | "safe" \| "fast" \| "science" \| "balanced" \| null | si es null, se usan `weights` |
| weights | {slope, rough, risk, science: float} \| null | cada uno en [0, 10] |
| habitat | {lat, lon} \| null | centro del radio máximo |
| max_radius_m | float \| null | (0, 100 000]; por ejemplo 10 000 = walkback |
| use_forbidden_zones | bool | por defecto true |

**`RouteOut`**

| Campo | Tipo | Notas |
|---|---|---|
| status | "ok" \| "no_route" | |
| reason | str \| null | solo si es `no_route` |
| geometry | GeoJSON LineString | lon/lat −180..180 |
| distance_m | float | 3D |
| straight_line_m | float | |
| tortuosity | float | NASA usa ~2 como referencia |
| max_slope_deg | float | |
| mean_slope_deg | float | |
| elevation_gain_m | float | |
| elevation_loss_m | float | |
| pct_risk_cells | float | 0–100 |
| est_time_h | float | |
| profile | list[{d_m: float, elev_m: float}] | máximo 500 puntos (submuestreo) |
| explanations | list[str] | ≥ 1 |
| weights_used | {slope, rough, risk, science} | |
| compute_ms | int | |

## Flujo técnico paso a paso

1. Pydantic valida el `RouteRequest`, se resuelve la región con el registro
   (002) y se aplica el rate limit.
2. Se convierten el inicio y el destino a fila/columna y se validan contra
   el bbox, la máscara de bloqueo y las zonas prohibidas (422 si fallan).
3. Se construye o se toma de la caché el mapa de costos para
   `(region, weights, constraints)`.
4. Se corre A\* con un timeout (5 s). Si no hay camino, se devuelve
   `no_route` con la razón.
5. Se calculan las métricas y el perfil, se generan las explicaciones
   comparando con la línea recta y se devuelve `RouteOut`.
6. El frontend dibuja la LineString como capa `line`, el perfil en canvas y
   el reporte con las explicaciones.

## Consideraciones de seguridad específicas de esta feature

- **Abuso de cómputo**: rate limit por IP y timeout duro en A\*. Los pesos
  y el radio tienen rangos acotados.
- La caché del mapa de costos tiene un tamaño máximo (LRU) para que pesos
  arbitrarios no agoten la memoria.
- Las explicaciones se arman con plantillas del servidor y se pintan con
  `textContent`.
