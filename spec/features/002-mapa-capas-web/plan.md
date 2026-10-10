# Plan — 002 Mapa por capas web

## Enfoque técnico

La API en FastAPI lee el registro de regiones y el `metadata.json` de cada
región al arrancar, y construye una **lista blanca** de
`(region_id, layer_id) → ruta de archivo`. Las capas se colorean a PNG con
paletas definidas en el código (Pillow + NumPy) y se cachean en memoria. El
frontend con Vite y MapLibre GL JS usa un estilo vacío con fondo oscuro y
agrega cada capa como fuente `image` con las cuatro esquinas del bbox.
MapLibre trata las coordenadas como lon/lat genéricas, lo cual sirve para
una región pequeña de Marte. La proyección Web Mercator distorsiona ~5% a
18° de latitud: es aceptable para la demo y se declara en `limitations` de
cada capa. Las distancias se calculan siempre en el backend, nunca en el
mapa.

## Archivos a crear/modificar

**Backend**
- `src/marsmap/api/main.py`: app FastAPI, CORS, routers y manejador de
  errores genérico.
- `src/marsmap/api/settings.py`: configuración (`DATA_DIR`,
  `CORS_ORIGINS`) desde variables de entorno.
- `src/marsmap/api/registry.py`: lista blanca de regiones y capas al
  arrancar.
- `src/marsmap/api/render.py`: `render_png(layer_id, array)` con paletas y
  nodata transparente.
- `src/marsmap/api/routers/regions.py`: endpoints de regiones, capas,
  imagen y celda.
- `src/marsmap/api/schemas.py`: modelos Pydantic de respuesta.
- `tests/api/test_regions.py`
- `tests/api/test_security.py`
- `.env.example`: `DATA_DIR`, `CORS_ORIGINS` (sin secrets).

**Frontend**
- `frontend/package.json`: Vite, MapLibre GL JS, Vitest y Playwright.
- `frontend/index.html`: estructura semántica con `<h1>`, mapa y panel de
  capas.
- `frontend/src/main.js`: arranque.
- `frontend/src/api.js`: cliente de la API.
- `frontend/src/map.js`: creación del mapa y manejo de fuentes y capas.
- `frontend/src/layersPanel.js`: toggles, opacidad, leyenda y ficha de
  fuente.
- `frontend/src/cellPopup.js`: popup de consulta de celda.
- `frontend/src/styles/index.css`: sistema de diseño (tema oscuro marciano,
  tipografía Inter u Outfit, tokens).
- `frontend/tests/layersPanel.test.js`: Vitest.
- `frontend/e2e/map.spec.js`: Playwright.

## Endpoints

| Método | Path | Descripción |
|---|---|---|
| GET | `/api/health` | Estado del servicio |
| GET | `/api/regions` | Lista de regiones disponibles con bbox |
| GET | `/api/regions/{region_id}/layers` | Metadatos y leyenda de cada capa de la región |
| GET | `/api/regions/{region_id}/layers/{layer_id}/image` | PNG coloreado de la capa (nodata transparente) |
| GET | `/api/regions/{region_id}/cell?lat=&lon=` | Valores de todas las capas en una coordenada |

## Modelo de datos

**`RegionOut`**

| Campo | Tipo | Notas |
|---|---|---|
| region_id | str | `^[a-z0-9_]+$` |
| name | str | |
| bbox | list[float] (4) | lon −180..180 E |

**`LayerOut`**: los campos de `LayerMetadata` (001), más:

| Campo | Tipo | Notas |
|---|---|---|
| legend | list[{value: float, color: str, label: str}] | color en `#rrggbb` |
| image_url | str | ruta relativa al endpoint de imagen |

**`CellOut`**

| Campo | Tipo | Notas |
|---|---|---|
| lat | float | eco del input |
| lon | float | normalizado −180..180 |
| elevation_m | float \| null | null si es nodata |
| slope_deg | float \| null | |
| roughness_m | float \| null | |
| traversability | int \| null | 0, 1, 2 |

**`ErrorOut`**: `{ "error": str, "code": str }`, sin stack trace.

## Flujo técnico paso a paso

1. Al arrancar, `registry` lee `regions.yaml` y, para cada región,
   `data/processed/<region>/metadata.json`. Si una capa declarada no existe
   en el disco, se omite y se registra una advertencia.
2. `GET /layers` devuelve los metadatos con su leyenda.
3. `GET /image` busca `(region_id, layer_id)` en la lista blanca (si no
   está, 404), lee el raster, lo colorea y devuelve el PNG con
   `Cache-Control`.
4. `GET /cell` valida lat/lon con Pydantic, verifica que caigan dentro del
   bbox, convierte la coordenada a fila/columna con la transformación
   inversa y lee el valor de cada capa.
5. El frontend pide `/regions` y `/layers`, crea una fuente `image` por
   capa con el bbox y arma el panel.
6. El usuario activa o desactiva capas y ajusta la opacidad
   (`setPaintProperty('raster-opacity')`). Al hacer clic se llama a `/cell`
   y se muestra el popup.

## Consideraciones de seguridad específicas de esta feature

- **Path traversal**: los archivos solo se resuelven por la lista blanca,
  nunca concatenando el `layer_id` a una ruta.
- **CORS** restringido a `CORS_ORIGINS` (por defecto
  `http://localhost:5173`).
- **XSS**: los metadatos y las etiquetas se pintan con `textContent`.
- **Errores**: un manejador global convierte las excepciones en `ErrorOut`
  genérico, y el detalle va solo al log.
