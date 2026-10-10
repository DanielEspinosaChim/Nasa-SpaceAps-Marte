# Datos

```
data/
├── raw/<region>/            # DEM descargado de NASA/USGS (NO se sube a git)
└── processed/<region>/      # capas generadas + GeoJSON de la región
    ├── elevation.tif  slope.tif  roughness.tif  hillshade.tif  traversability.tif
    ├── metadata.json        # fuente, instrumento, resolución y limitaciones por capa
    ├── poi.geojson          # puntos de interés (se versiona)
    └── forbidden_zones.geojson
```

Los `.tif` están en `.gitignore`: se regeneran con el comando de abajo. Los `.geojson`
sí se versionan, y `terrain.build` los conserva al regenerar las capas.

## Generar capas

Sin datos de NASA (terreno sintético determinista, para desarrollo y demo offline):

```
python -m marsmap.terrain.build --region jezero --synthetic --seed 42
```

Con el DEM real de Jezero:

1. Recortar el DEM MOLA–HRSC (200 m) o MOLA (463 m) a Jezero. El archivo global pesa
   varios GB: **no lo descargues completo**.
   [MOLA–HRSC 200 m](https://astrogeology.usgs.gov/search/map/mars_mgs_mola_mex_hrsc_blended_dem_global_200m) ·
   [MOLA 463 m](https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m)
   ```
   python scripts/fetch_dem.py --region jezero --url <URL_DEL_GEOTIFF>   # o --source <archivo local>
   ```
   Con `--url` solo se aceptan dominios `*.usgs.gov`, `*.nasa.gov` y `*.wustl.edu`.
   Alternativa manual: Mars Trek (trek.nasa.gov/mars) permite descargar un recorte.
2. `python -m marsmap.terrain.build --region jezero --source data/raw/jezero/dem.tif`

Convención: longitud −180..180 positiva al Este (los datos en 0–360 se convierten),
latitud planetocéntrica, datum Mars 2000 (esfera de 3 396 190 m).

## `poi.geojson` — sitios de muestras REALES de Mars 2020

Generado desde la capa pública «Sampling Locations» de NASA/JPL (`M20_SAMPLE_v3.json`):

```
python -m marsmap.data.mars2020 --region jezero
```

Descarga (solo https, dominios `*.nasa.gov`, con tope de tamaño) los sitios de muestras, los
waypoints, el recorrido y el depósito de muestras a `data/raw/jezero/mars2020/` (no se versiona), y
escribe `poi.geojson` con **22 sitios reales** y el sitio de aterrizaje publicado por NASA
(`landing_site`: primer waypoint, sol 13 → 18.44462715° N, 77.45088572° E).

Cada punto conserva los campos de NASA (`sol`, `location`, `sample_type`, `rock_type`) y su `source`.

> **Qué es dato de NASA y qué es criterio del proyecto.** Las coordenadas, nombres, sol, lugar,
> tipo de muestra y litología son de NASA. El `science_value` **no**: NASA no publica un valor
> numérico. Se calcula con una rúbrica del proyecto (`marsmap/data/mars2020.py`): base por tipo de
> muestra (núcleo de roca 0.70, regolito 0.40, atmosférica 0.20) + bono por evidencia de agua o
> alteración (serpentinita y carbonato silíceo +0.25, sedimentaria +0.20, impactita +0.10, ígnea
> +0.05) + 0.05 si es núcleo doble. El `dwell_time_h` (2 h por muestra de roca) es un supuesto.
> Debe presentarse como criterio del equipo, no como valoración de NASA.

## `forbidden_zones.geojson`

Polígonos o puntos con `properties.name` y `properties.buffer_m` (búfer en metros).
Ejemplo (zona de protección planetaria, círculo aproximado con búfer de 50 m):

```json
{"type": "Feature",
 "properties": {"name": "RSL (ejemplo)", "buffer_m": 50},
 "geometry": {"type": "Polygon", "coordinates": [[[77.5,18.5],[77.52,18.5],[77.52,18.52],[77.5,18.52],[77.5,18.5]]]}}
```
