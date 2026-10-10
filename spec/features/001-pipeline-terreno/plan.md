# Plan — 001 Pipeline de terreno

## Enfoque técnico

Se lee el DEM con **Rasterio** usando una ventana del bbox de la región, sin
cargar el archivo global completo. Las capas se derivan con **NumPy/SciPy**:
la pendiente con gradiente de Horn y tamaño de celda en metros corregido por
latitud; la rugosidad como desviación estándar de la elevación en una
ventana de 3×3; el hillshade con azimut de 315° y altitud de 45°; y la
transitabilidad por umbrales. Las regiones se definen en un YAML versionado,
para que cambiar o agregar regiones no requiera tocar código. El generador
sintético produce un DEM con cráteres, colinas y ruido fractal, y pasa por
**exactamente el mismo pipeline**.

Fuente principal: **MOLA–HRSC Blended DEM Global 200 m v2** (USGS
Astrogeology). Alternativa ligera: MOLA DEM 463 m.
El recorte lo hace `scripts/fetch_dem.py`, que acepta una URL (leída con
`/vsicurl/` de GDAL, solo dominios en lista blanca) o un archivo local. Si
la lectura remota es lenta porque el archivo no es COG, se descarga una
sola vez y se recorta en local: el pipeline solo necesita el recorte en
`data/raw/jezero/`.

## Archivos a crear/modificar

- `pyproject.toml`: proyecto `marsmap`, dependencias y configuración de
  ruff y pytest.
- `src/marsmap/__init__.py`: paquete.
- `src/marsmap/config/regions.yaml`: región `jezero` (bbox
  `[77.0, 18.0, 78.0, 18.9]`, nombre y descripción).
- `src/marsmap/config/regions.py`: carga y validación (Pydantic) de
  regiones.
- `src/marsmap/geo/coords.py`: `normalize_lon()`, constantes de Marte
  (radio 3 396 190 m) y `cell_size_m(transform, lat)`.
- `src/marsmap/terrain/dem.py`: `read_dem_window(path, bbox)` → arreglo,
  transformación, CRS y nodata.
- `src/marsmap/terrain/synthetic.py`: `generate_dem(bbox, shape, seed)`.
- `src/marsmap/terrain/derive.py`: `slope_deg()`, `roughness()`,
  `hillshade()` y `traversability()`.
- `src/marsmap/terrain/metadata.py`: modelo `LayerMetadata` y escritura de
  `metadata.json`.
- `src/marsmap/terrain/build.py`: CLI (`argparse`) y orquestación con
  escritura atómica (carpeta temporal, que se renombra al terminar).
- `tests/terrain/test_coords.py`
- `tests/terrain/test_derive.py`
- `tests/terrain/test_synthetic.py`
- `tests/terrain/test_build.py`
- `data/README.md`: qué va en `raw/` y en `processed/`, y cómo descargar el
  DEM.

## Endpoints

No aplica: esta feature es una librería y una CLI. Las capas se exponen por
HTTP en la feature 002.

## Modelo de datos

**Capas raster de salida** (`data/processed/<region>/`)

| Capa | Archivo | Tipo | Unidades | Nodata |
|---|---|---|---|---|
| elevation | `elevation.tif` | float32 | m (sobre el datum Mars 2000) | NaN |
| slope | `slope.tif` | float32 | grados | NaN |
| roughness | `roughness.tif` | float32 | m (desv. estándar 3×3) | NaN |
| hillshade | `hillshade.tif` | uint8 | 0–255 | 0 |
| traversability | `traversability.tif` | uint8 | 0 segura, 1 riesgo, 2 bloqueada | 255 |

**`LayerMetadata`** (una entrada por capa en `metadata.json`)

| Campo | Tipo | Notas |
|---|---|---|
| layer_id | str | requerido, único dentro de la región, `^[a-z_]+$` |
| name | str | nombre legible |
| units | str | requerido |
| source_dataset | str | por ejemplo `MOLA_HRSC_Blend_200m_v2` o `synthetic` |
| instrument | str | por ejemplo `MGS MOLA + MEX HRSC` |
| resolution_m | float | > 0 |
| crs | str | WKT o código del CRS |
| bbox | list[float] (4) | `[lon_min, lat_min, lon_max, lat_max]`, lon −180..180 E |
| generated_at | str | ISO 8601 UTC |
| limitations | str | por ejemplo "200 m/píxel: no resuelve rocas individuales" |

**`Region`** (`regions.yaml`)

| Campo | Tipo | Notas |
|---|---|---|
| region_id | str | `^[a-z0-9_]+$`, único |
| name | str | requerido |
| bbox | list[float] (4) | validado: min < max y dentro de rango |
| description | str | opcional |

## Flujo técnico paso a paso

1. La CLI parsea los argumentos (`--region`, `--source` o `--synthetic`,
   `--seed`, `--out`).
2. Carga y valida la región desde `regions.yaml`. Normaliza las longitudes.
3. Obtiene el DEM: lee la ventana del bbox con Rasterio, o lo genera
   sintético con la semilla.
4. Convierte nodata a NaN y calcula el tamaño de celda en metros por fila
   (corrección por cos(lat)).
5. Deriva la pendiente, la rugosidad, el hillshade y la transitabilidad.
6. Escribe los GeoTIFF y `metadata.json` en una carpeta temporal.
7. Valida que todas las capas compartan forma, transformación y CRS.
8. Renombra la carpeta temporal a `data/processed/<region>/` y reemplaza la
   anterior solo si todo salió bien.

## Consideraciones de seguridad específicas de esta feature

- `region_id` se valida con regex y contra el YAML. Nunca se usa un texto
  libre para construir rutas de salida.
- No se ejecutan comandos de sistema con inputs (nada de `subprocess` con
  rutas del usuario).
- La descarga remota, si se agrega, solo se permite desde dominios en lista
  blanca (`*.usgs.gov`, `*.nasa.gov`, `*.wustl.edu`).
