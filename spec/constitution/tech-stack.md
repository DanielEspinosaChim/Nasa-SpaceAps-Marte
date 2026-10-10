# Tech Stack

## Lenguaje

- **Python 3.11+**: datos geoespaciales, planificación, simulación y ML.
- **JavaScript (ES2022, módulos)**: frontend web.

## Framework / runtime

**Backend y ML (paquete `marsmap` en `src/`)**
- **FastAPI + Uvicorn**: API que expone capas, rutas, misiones y simulación.
- **Pydantic v2**: validación de todos los inputs y del modelo de datos.
- **NumPy / SciPy**: pendiente, rugosidad y operaciones raster.
- **Rasterio (GDAL)**: lectura y escritura de GeoTIFF, recortes y CRS.
- **GeoPandas / Shapely**: zonas prohibidas, búferes y GeoJSON.
- **pymoo**: algoritmo genético multiobjetivo NSGA-II para la selección de
  misiones.
- **PyTorch + torchvision**: CNN de terreno (AI4Mars) y autoencoder
  detector de novedad.
- **Pillow**: renderizado de capas a PNG para el mapa.

**Frontend (`frontend/`)**
- **Vite + JavaScript vanilla + CSS vanilla**.
- **MapLibre GL JS**: mapa 2D por capas (imagen georreferenciada sobre
  coordenadas de Marte).
- **CesiumJS** (opcional, etapa posterior): vista 3D del relieve.

## Base de datos

**No hay base de datos en el MVP.** Los datos procesados se guardan como
archivos:
- `data/processed/<region>/*.tif` (capas raster GeoTIFF)
- `data/processed/<region>/*.geojson` (zonas, puntos de interés, rutas)
- `data/processed/<region>/metadata.json` (fuente, instrumento, resolución,
  fecha y limitaciones de cada capa)

Los datos crudos de NASA van en `data/raw/` y **no se suben al repositorio**.

## Testing

- **pytest**: unit e integración del paquete `marsmap` y de la API
  (`fastapi.testclient`).
- **Vitest**: lógica del frontend.
- **Playwright**: E2E del flujo principal en el navegador.
- Todas las pruebas de algoritmos usan **terreno sintético determinista**
  (con semilla) para no depender de la red ni de archivos de NASA.

## Otras herramientas relevantes

- **ruff**: linter y formateador de Python.
- **pip + venv** con `pyproject.toml` como gestor de dependencias. Las
  ruedas de Rasterio ≥ 1.4 traen GDAL incluido, verificado en Windows 11
  sin conda.
- **npm**: gestor de paquetes del frontend.
- **GPU local: NVIDIA GeForce RTX 5060 Laptop (8 GB)**, detectada con `nvidia-smi`. Se usa
  para entrenar la CNN y el autoencoder (007, 008) con PyTorch; Colab queda de respaldo. El
  genético (004) corre en CPU a propósito: ver `docs/decisiones.md` (D8).
- CI/CD: no definido para el hackathon.

## Convenciones de datos geoespaciales

- Cuerpo y datum: **Mars 2000 (IAU), esfera de radio 3 396 190 m**.
- Longitud interna: **−180° a 180°, positiva hacia el Este**. Todo dato de
  entrada en 0–360° E se convierte al cargarse.
- Latitud planetocéntrica.
- Región de demostración: **cráter Jezero, centro ≈ 18.4° N, 77.5° E**.
- Unidades: metros, grados y segundos (SI) en todo el código.

## Convenciones de versión

- Python ≥ 3.11
- Node.js ≥ 20

---

*Decidido en la entrevista inicial. Si se cambia algo del stack más
adelante, actualizar este archivo primero (nivel spec-anchored) antes de
tocar código.*
