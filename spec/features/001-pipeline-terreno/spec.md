# Spec — 001 Pipeline de terreno

**Estado: LISTO PARA IMPLEMENTAR** (revisado el 2026-10-09)

## Qué hace

Convierte un modelo digital de elevación (DEM) de NASA/USGS de la región de
Jezero en las capas base del proyecto: **elevación, pendiente, rugosidad,
sombreado (hillshade) y transitabilidad**. Cada capa se guarda como GeoTIFF
con el mismo tamaño, georreferencia y CRS, junto con un `metadata.json` que
documenta fuente, instrumento, resolución y limitaciones.

Incluye un **generador de terreno sintético** con la misma interfaz, para
desarrollar, probar y hacer la demo sin red ni datos de NASA.

## Módulos que toca

- [x] Backend (paquete `marsmap.terrain` y CLI)
- [ ] Frontend

## Depende de

- Ninguna (es la primera feature).

## Fuera de alcance

- Servir las capas por HTTP o mostrarlas en el mapa (eso es la 002).
- DTMs de HiRISE/CTX de alta resolución: solo se deja la interfaz preparada
  para agregarlos después.
- Clasificación de terreno por imágenes (eso es la 007).
- Mosaicos de varias escenas o reproyección a otros cuerpos.

## Criterios de aceptación

1. Dado un DEM de entrada y la región `jezero`, el comando
   `python -m marsmap.terrain.build --region jezero --source <dem>` genera
   en `data/processed/jezero/` los archivos `elevation.tif`, `slope.tif`,
   `roughness.tif`, `hillshade.tif` y `traversability.tif`, todos con el
   mismo ancho, alto, transformación afín y CRS.
2. Sobre un plano sintético inclinado con ángulo conocido θ (por ejemplo
   5°, 12° y 20°), la pendiente calculada en las celdas interiores es
   θ ± 0.5°.
3. La pendiente se calcula con el tamaño real de celda en metros: la
   distancia horizontal en X se corrige por cos(latitud) cuando el CRS es
   equirectangular en grados. Un test con el mismo plano a 0° y a 60° de
   latitud da la misma pendiente física (± 0.5°).
4. La transitabilidad sigue los umbrales de Perseverance: pendiente
   `< 10°` → `0` (segura), `10° ≤ p ≤ 15°` → `1` (riesgo), `> 15°` → `2`
   (bloqueada). Un test verifica los valores en 9.99°, 10°, 15° y 15.01°.
5. Las celdas sin dato (nodata) del DEM se propagan como nodata en todas las
   capas derivadas y nunca se tratan como terreno plano ni seguro.
6. `metadata.json` contiene, para cada capa: `layer_id`, `name`, `units`,
   `source_dataset`, `instrument`, `resolution_m`, `crs`, `bbox`
   (`[lon_min, lat_min, lon_max, lat_max]`, con longitudes de −180 a 180 E),
   `generated_at` (ISO 8601) y `limitations`.
7. Las longitudes de entrada en convención 0–360° E se convierten a
   −180–180°. Un test verifica que 282.5 → −77.5, que 77.5 → 77.5 y que
   180 → 180 o −180 de forma consistente.
8. `--synthetic --seed N` genera el mismo conjunto de archivos sin red, y el
   resultado es idéntico byte a byte para la misma semilla.
9. Un bbox inválido (lat_min ≥ lat_max, fuera de rango) o fuera de la
   cobertura del DEM termina con código de salida distinto de 0 y un mensaje
   claro, sin dejar archivos parciales en la carpeta de salida.
10. Procesar la región de Jezero (≈ 1° × 1° a 200 m/píxel) tarda menos de
    30 s en una laptop normal.
