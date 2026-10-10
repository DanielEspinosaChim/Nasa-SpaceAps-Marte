# Spec — 002 Mapa por capas web

**Estado: LISTO PARA IMPLEMENTAR** (revisado el 2026-10-09)

## Qué hace

Expone las capas generadas en la 001 mediante una API FastAPI y las muestra
en un mapa web MapLibre por capas. El usuario puede activar o desactivar
cada capa, ajustar su opacidad, ver la leyenda y la ficha de fuente de cada
una (misión, instrumento, resolución y limitaciones) y hacer clic en
cualquier punto para consultar sus valores: elevación, pendiente,
rugosidad y transitabilidad. Es la "vista integrada y por capas" que pide el
reto.

## Módulos que toca

- [x] Backend (`marsmap.api`)
- [x] Frontend (`frontend/`)

## Depende de

- 001-pipeline-terreno (capas y `metadata.json` en `data/processed/<region>/`).

## Fuera de alcance

- Rutas y misiones (003 y 004).
- Vista 3D (backlog).
- Teselas (XYZ/WMTS) dinámicas: el MVP sirve una imagen PNG por capa
  georreferenciada por bbox, suficiente para una región de ~300×300 px.
- Basemap externo de Mars Trek (opcional, en backlog). El fondo es el
  hillshade propio.

## Criterios de aceptación

1. `GET /api/health` responde `200 {"status":"ok"}`.
2. `GET /api/regions` devuelve una lista con al menos `jezero`, con su
   `region_id`, `name` y `bbox` (lon −180..180 E).
3. `GET /api/regions/jezero/layers` devuelve las 5 capas de la 001 con todos
   los campos de `LayerMetadata` más `legend` (lista de pares
   valor/color/etiqueta).
4. `GET /api/regions/jezero/layers/{layer_id}/image` devuelve
   `image/png` con la capa coloreada según su paleta, y las celdas nodata
   son transparentes.
5. Un `region_id` o `layer_id` inexistente, o con caracteres fuera de
   `^[a-z0-9_]+$` (por ejemplo `..%2F..%2Fetc`), devuelve 404 o 422 y nunca
   lee un archivo fuera de `data/processed/`.
6. `GET /api/regions/jezero/cell?lat=18.4&lon=77.5` devuelve `elevation_m`,
   `slope_deg`, `roughness_m` y `traversability` de esa celda. Una
   coordenada fuera del bbox devuelve 422 con un mensaje claro.
7. En el frontend se ven las 5 capas en un panel. Cada una se puede
   activar o desactivar y tiene un slider de opacidad (0–100%) que se
   refleja en el mapa en menos de 100 ms.
8. Al hacer clic en el mapa aparece un popup con los valores de la celda
   (criterio 6), con unidades.
9. La ficha de cada capa muestra la fuente, el instrumento, la resolución y
   las limitaciones tomadas de la API. El texto se inserta con
   `textContent`, nunca con `innerHTML`.
10. Con datos sintéticos (`--synthetic`) toda la app funciona sin conexión
    a internet. Las librerías del frontend vienen empaquetadas, no de un
    CDN.
11. La primera carga de la página con la región de Jezero tarda menos de
    3 s en local.
