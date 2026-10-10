# Tasks — 003 Planificador A\*

Checklist de tareas atómicas y verificables. Marcar `[x]` solo cuando esté
implementado Y verificado, no solo escrito.

## Backend

- [x] Agregar shapely y geopandas a `pyproject.toml`
- [x] Implementar `presets.py` (safe, fast, science y balanced; balanced
      lo usa la matriz de tramos de la 004)
- [x] Implementar `constraints.py`: rasterizar zonas prohibidas con búfer
      en metros
- [x] Implementar `constraints.py`: máscara del radio máximo desde el
      hábitat
- [x] Implementar `costmap.py` con normalización de pendiente y rugosidad
      y bloqueo
- [x] Implementar `dijkstra.py` de referencia
- [x] Implementar `astar.py` con heurística admisible y timeout
- [x] Implementar `metrics.py` (distancia 3D, tortuosidad, pendientes,
      desnivel, perfil y tiempo)
- [x] Implementar `explain.py` (comparación con la línea recta y plantillas
      con cifras)
- [x] Implementar `ratelimit.py` (por IP, configurable por variable de
      entorno)
- [x] Implementar `POST /route` y `GET /route/presets`
- [x] Crear `forbidden_zones.geojson` y `poi.geojson` provisionales para
      Jezero
- [ ] Calibrar presets con el DEM real de Jezero
      <!-- falta: requiere el DEM real de Jezero -->

## Frontend

- [x] `routePlanner.js`: modo "elegir inicio/destino" con marcadores
      arrastrables
- [x] Selector de preset (segura / rápida / científica) y botón "Calcular
      ruta"
- [x] Dibujar la ruta como capa `line` con animación de trazo
- [x] `profileChart.js`: perfil altimétrico en canvas, sombreando los
      tramos de riesgo
- [x] `routeReport.js`: tarjeta de métricas y lista de explicaciones con
      `textContent`
- [x] Mostrar `no_route` y los errores 422 de forma clara al usuario

## Tests unitarios

- [x] Muro con hueco: la ruta pasa por el hueco
- [x] Optimalidad: A\* = Dijkstra en 20 mapas sintéticos de 50×50
- [x] Restricciones: 0 violaciones en 100 rutas aleatorias (bloqueo, zonas
      y radio)
- [x] Búfer de zona prohibida: una celda a 10 m del borde con búfer de
      50 m queda bloqueada
- [x] Métricas: en un plano, la tortuosidad de la línea recta es 1.0 ±
      0.05
- [x] Explicaciones: siempre ≥ 1 y contienen al menos un número
- [x] Presets: `max_slope(safe)` ≤ `max_slope(fast)` y
      `distance(fast)` ≤ `distance(safe)`

## Tests de integración

- [x] `POST /route` con un preset válido devuelve 200 con todos los campos
      de `RouteOut`
- [x] Inicio en celda bloqueada → 422 `start_blocked`
- [x] Destino aislado → 200 `status: no_route`
- [x] Rendimiento: 300×300 en menos de 2 s

## Tests de seguridad

- [x] Validación de inputs cubierta con test (pesos fuera de rango, radio
      negativo, coordenadas inválidas → 422)
- [x] Rate limit: exceder el límite devuelve 429
- [x] Timeout: un mapa patológico devuelve un error controlado, no cuelga
      el servidor
- [x] Control de acceso: endpoint público de cómputo sin escritura
      persistente, documentado
- [x] Test de aislamiento multi-tenant: no aplica en este proyecto (ver
      checklist 000, punto 3)
- [ ] Revisar contra `spec/features/000-seguridad-transversal/spec.md`
      antes de mergear
      <!-- falta: pasar el subagente auditor-seguridad -->

## E2E

- [x] Playwright: abrir el mapa → elegir inicio y destino en Jezero →
      preset "segura" → se dibuja la ruta → se ven las métricas, el perfil
      y al menos una explicación → cambiar a "rápida" → la distancia mostrada
      es menor o igual

---

*Al completar una tarea, márcala con `[x]`. Si surge una tarea nueva no
prevista, agrégala al final de su sección correspondiente en vez de
modificar las ya existentes. Si una tarea queda parcial, déjala en `[ ]`
con una nota `<!-- parcial: falta X -->`.*
