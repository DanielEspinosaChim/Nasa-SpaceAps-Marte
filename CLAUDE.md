# Mars Scout — Martian Map (NASA Space Apps 2026)

Rover autónomo simulado que usa el mapa satelital de NASA para proponer,
planificar, visitar y reportar zonas de interés en el cráter Jezero, y que
entrega a astronautas y planificadores de misión un mapa por capas mejorado
con rutas seguras y explicadas. Reto: *Interplanetary Survival Guide:
Martian Map*.

## Stack

- Lenguaje: Python 3.11+ (backend, datos y ML) · JavaScript ES2022 (frontend)
- Framework / runtime: FastAPI + Uvicorn · NumPy/SciPy · Rasterio ·
  GeoPandas/Shapely · pymoo (NSGA-II) · PyTorch · Vite + MapLibre GL JS
- Base de datos: ninguna en el MVP. Archivos GeoTIFF, GeoJSON y JSON en
  `data/processed/`
- Tests: pytest (backend) · Vitest (frontend) · Playwright (E2E)

## Comandos

Verificados el 2026-10-09 (Windows 11, Python 3.12, Node 24).

- Instalación: `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"` y
  `npm --prefix frontend install`
- Datos de demo (sintéticos): `python -m marsmap.terrain.build --region jezero --synthetic --seed 42`
- Datos reales de NASA: `python scripts/fetch_dem.py --region jezero --url <GeoTIFF MOLA–HRSC>` y
  `python -m marsmap.terrain.build --region jezero --source data/raw/jezero/dem.tif`; sitios de
  muestras: `python -m marsmap.data.mars2020 --region jezero` (URLs en `data/README.md`)
- Pruebas con el DEM real: `pytest tests/real` (se omiten si falta `data/raw/jezero/dem.tif`)
- Todo en uno (producción local): `npm --prefix frontend run build` y luego
  `FRONTEND_DIST=frontend/dist uvicorn marsmap.api.main:app --app-dir src` sirve la API y la web
  en http://localhost:8000
- E2E: con el backend arriba en :8000, `npm --prefix frontend run e2e`
  (Playwright ≥ 1.5x; la 1.49 se cuelga con Node 24)

- `uvicorn marsmap.api.main:app --reload --app-dir src`: arranca la API en
  local
- `npm --prefix frontend run dev`: arranca el frontend en local
  (http://localhost:5173)
- `python -m marsmap.terrain.build --region jezero --synthetic --seed 42`:
  genera capas sintéticas
- `pytest`: tests de backend (deben pasar antes de cada commit; `-m "not slow"` omite los de calidad y rendimiento)
- `npm --prefix frontend test`: tests del frontend
- `ruff check . && ruff format --check .`: estilo de Python (antes de cada
  PR)
- `npm --prefix frontend run build`: build de producción del frontend

## Estructura del proyecto

- `src/marsmap/`: paquete Python principal
  - `config/`: regiones (`regions.yaml`) y su validación
  - `geo/`: coordenadas de Marte, normalización de longitud y tamaño de
    celda
  - `terrain/`: pipeline del DEM a las capas (001)
  - `planning/`: mapa de costos, A\*, Dijkstra, métricas y explicaciones
    (003); genético (004)
  - `sim/`: simulación del rover y peligros ocultos (006)
  - `vision/`: CNN de AI4Mars y detector de novedad (007, 008)
  - `api/`: FastAPI, routers, esquemas y rate limit
- `tests/`: espejo de `src/marsmap/` (`tests/terrain/`,
  `tests/planning/`, `tests/api/`…)
- `frontend/`: app Vite + MapLibre (`src/`, `tests/`, `e2e/`)
- `data/raw/`: datos crudos de NASA/USGS (**no se suben a git**)
- `data/processed/<region>/`: capas procesadas y `metadata.json`
- `spec/`: constitución y specs de features (SDD)
- `docs/`: memoria de sesión y registro de decisiones

## Convenciones

- Python: `snake_case` para funciones y variables, `PascalCase` para
  clases, tipado en todas las funciones públicas, formateo con ruff.
- JS: `camelCase`, módulos ES y un archivo por componente de UI.
- Tests en `tests/` con la misma ruta que el módulo
  (`src/marsmap/planning/astar.py` → `tests/planning/test_astar.py`).
- Toda entrada de la API se valida con modelos Pydantic. Los errores al
  cliente salen como `ErrorOut {error, code}`, sin stack traces.
- **Coordenadas**: longitud interna de −180 a 180 positiva al Este,
  latitud planetocéntrica y datum Mars 2000 (R = 3 396 190 m). Todo dato de
  entrada en 0–360° se convierte al cargarse. Jezero está en **+18.4° N**,
  77.5° E.
- Unidades SI (m, s, grados) en todo el código. Las unidades se incluyen en
  el nombre del campo cuando no son obvias (`distance_m`, `slope_deg`).
- Toda capa conserva sus metadatos (fuente, instrumento, resolución,
  fecha y limitaciones) y la UI los muestra.
- Los algoritmos se prueban con **terreno sintético determinista**
  (semilla fija), nunca dependiendo de la red.
- En el frontend, el texto que viene de la API se inserta con
  `textContent`, nunca con `innerHTML`.

## No hagas

- No instalar dependencias sin avisar.
- No subir archivos `.env*` ni ninguna credencial al repositorio.
- No borrar código o archivos sin confirmar explícitamente conmigo.
- No subir datos crudos ni rasters pesados (`data/raw/`, `*.tif` > 10 MB) a
  git.
- No mezclar convenciones de longitud (0–360 frente a −180–180) ni usar
  latitudes sin verificar contra la fuente.
- No presentar los datos históricos de InSight como clima actual ni como
  datos de Jezero.
- No usar el algoritmo genético para tareas que A\*/Dijkstra resuelven de
  forma exacta (rutas punto a punto).
- No citar datos o noticias en el pitch o la UI sin una fuente verificada.

## Flujo de trabajo

- Para tareas grandes, refactors, o cambios que toquen más de 2 archivos:
  usa Plan Mode. Muestra el plan completo y espera mi OK explícito antes
  de tocar código.
- Para bugs evidentes, correcciones puntuales o tareas atómicas de un solo
  archivo: usa Build Mode y ejecuta directo.
- Una tarea a la vez; al terminar, dime qué cambiaste para que lo revise.
- Si no estás seguro al 80%, pregunta. No inventes.
- **`docs/` se actualiza solo, sin que yo lo pida.** Al cerrar cualquier
  tarea o sesión de trabajo relevante, agrega automáticamente una entrada
  en `docs/` con fecha, qué se hizo, qué quedó pendiente y qué decisiones
  se tomaron. Antes de empezar una tarea nueva, revisa `docs/` primero —
  si el contexto ya está documentado ahí, no me lo vuelvas a preguntar.
- Antes de implementar una feature, verifica que su spec cumpla la revisión
  y diga **LISTO PARA IMPLEMENTAR**. Al cerrar una feature, corre el bucle
  *Actuar → Observar → Corregir* hasta que pasen todos los tests.

## Subagentes disponibles

Definidos en `.claude/agents/`.

- **Coordinador**: no escribe código, divide tareas y decide el orden.
- **Implementador**: escribe el código de la subtarea asignada.
- **Tester**: corre y escribe tests, valida criterios de aceptación. No
  modifica código de producción.
- **Auditor de seguridad**: solo lectura. Revisa inyecciones, secrets,
  validación de inputs, control de acceso y dependencias con CVEs.
- **Validador científico**: solo lectura. Revisa coordenadas y convenciones
  de longitud, unidades, umbrales de terreno (10° y 15°, walkback de
  10 km), metadatos y fuentes de cada capa y las afirmaciones del pitch
  contra fuentes NASA/JPL/USGS. Puede leer `src/`, `data/processed/`,
  `spec/`, `docs/` y `frontend/src/`. No edita archivos; reporta hallazgos
  al Coordinador.

## MCPs configurados

- **Context7** (`.mcp.json`, servidor HTTP remoto): documentación
  actualizada de librerías (FastAPI, Rasterio, pymoo, MapLibre, PyTorch).
  Úsalo antes de escribir código contra una API de librería que no sea
  trivial.

## Documentación

- `spec/constitution/`: misión, stack y roadmap del proyecto.
- `spec/features/`: spec, plan y tasks de cada feature.
- `spec/features/000-seguridad-transversal/`: checklist de seguridad de
  referencia para auditar cualquier módulo.
- `docs/`: notas de sesión y memoria de trabajo.
- `docs/decisiones.md`: registro de decisiones de diseño (D1, D2…).
