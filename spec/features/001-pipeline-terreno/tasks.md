# Tasks — 001 Pipeline de terreno

Checklist de tareas atómicas y verificables. Marcar `[x]` solo cuando esté
implementado Y verificado, no solo escrito.

## Backend

- [x] Crear `pyproject.toml` con dependencias (numpy, scipy, rasterio,
      pydantic, pyyaml) y configuración de ruff y pytest
- [x] Crear `src/marsmap/config/regions.yaml` con la región `jezero`
- [x] Implementar `regions.py` (modelo `Region` con validación del bbox)
- [x] Implementar `geo/coords.py`: `normalize_lon()` y `cell_size_m()`
- [x] Implementar `terrain/dem.py`: lectura por ventana y nodata a NaN
- [x] Implementar `terrain/synthetic.py`: DEM determinista con cráteres,
      colinas y ruido
- [x] Implementar `slope_deg()` con gradiente de Horn y corrección por
      latitud
- [x] Implementar `roughness()` (desviación estándar 3×3, respetando NaN)
- [x] Implementar `hillshade()` (azimut 315°, altitud 45°)
- [x] Implementar `traversability()` con umbrales 10° y 15°
- [x] Implementar `metadata.py` (modelo `LayerMetadata` y escritura)
- [x] Implementar la CLI `terrain/build.py` con escritura atómica
- [x] Documentar en `data/README.md` la descarga del DEM y la estructura de
      carpetas
- [x] Descargar el DEM real de Jezero y generar las capas reales una vez
      (2026-10-09: MOLA_HRSC_Blend_200m_v2, 296×267 celdas, 93.7% segura / 4.1% riesgo / 2.2% bloqueada)
- [x] Script `scripts/fetch_dem.py`: recortar el bbox de Jezero del DEM
      MOLA–HRSC 200 m con Rasterio (`/vsicurl/` si el archivo es COG; si
      no, desde una copia local) y guardarlo en `data/raw/jezero/`, solo
      desde dominios en lista blanca

## Frontend

- [x] No aplica en esta feature

## Tests unitarios

- [x] `normalize_lon`: 282.5 → −77.5, 77.5 → 77.5 y el caso 180
- [x] Pendiente en un plano inclinado de 5°, 12° y 20° (± 0.5°)
- [x] Pendiente igual a latitud 0° y 60° (corrección por cos(lat))
- [x] Umbrales de transitabilidad en 9.99°, 10°, 15° y 15.01°
- [x] Propagación de nodata en todas las capas derivadas
- [x] Sintético determinista: misma semilla, mismos bytes

## Tests de integración

- [x] La CLI con `--synthetic` genera las 5 capas y `metadata.json`, con
      la misma forma, transformación y CRS
- [x] La CLI con un bbox inválido sale con código ≠ 0 y sin archivos
      parciales
- [x] `metadata.json` valida contra el modelo `LayerMetadata` con todos los
      campos requeridos
- [x] Rendimiento: región de 1° × 1° a 200 m en menos de 30 s

## Tests de seguridad

- [x] Validación de inputs cubierta con test (`region_id` con `../` o con
      caracteres inválidos se rechaza)
- [x] Control de acceso: no aplica (CLI local sin endpoints); queda
      documentado
- [x] Test de aislamiento multi-tenant: no aplica en este proyecto (ver
      checklist 000, punto 3)
- [ ] Revisar contra `spec/features/000-seguridad-transversal/spec.md`
      antes de mergear
      <!-- falta: pasar el subagente auditor-seguridad -->

## E2E

- [ ] Desde un clon limpio, correr
      `python -m marsmap.terrain.build --region jezero --synthetic --seed 42`
      y abrir `slope.tif` en QGIS con la georreferencia correcta
      <!-- falta: comprobación manual en QGIS (la georreferencia sí se valida por test) -->

---

*Al completar una tarea, márcala con `[x]`. Si surge una tarea nueva no
prevista, agrégala al final de su sección correspondiente en vez de
modificar las ya existentes. Si una tarea queda parcial, déjala en `[ ]`
con una nota `<!-- parcial: falta X -->`.*
