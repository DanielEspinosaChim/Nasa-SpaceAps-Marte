# Tasks — 002 Mapa por capas web

Checklist de tareas atómicas y verificables. Marcar `[x]` solo cuando esté
implementado Y verificado, no solo escrito.

## Backend

- [x] Agregar fastapi, uvicorn, pillow y httpx (para tests) a
      `pyproject.toml`
- [x] Implementar `settings.py` con `DATA_DIR` y `CORS_ORIGINS` y crear
      `.env.example`
- [x] Implementar `registry.py` (lista blanca de regiones y capas al
      arrancar)
- [x] Implementar `render.py` con paletas por capa y nodata transparente
- [x] Implementar `schemas.py` (`RegionOut`, `LayerOut`, `CellOut`,
      `ErrorOut`)
- [x] Implementar `GET /api/health` y `GET /api/regions`
- [x] Implementar `GET /api/regions/{id}/layers` con leyenda
- [x] Implementar `GET /api/regions/{id}/layers/{layer}/image` con caché
- [x] Implementar `GET /api/regions/{id}/cell` con validación de bbox
- [x] Manejador global de errores con `ErrorOut` y CORS configurado

## Frontend

- [x] Inicializar Vite (vanilla JS) en `frontend/` y agregar MapLibre GL JS
- [x] Sistema de diseño en `index.css`: tema oscuro marciano, tokens de
      color, tipografía y microanimaciones
- [x] `index.html` semántico con un solo `<h1>`, meta descripción e IDs
      únicos
- [x] `api.js`: cliente con manejo de errores
- [x] `map.js`: mapa con estilo vacío y fuentes `image` por capa
- [x] `layersPanel.js`: toggle, opacidad, leyenda y ficha de fuente con
      `textContent`
- [x] `cellPopup.js`: clic → `/cell` → popup con unidades

## Tests unitarios

- [x] `render_png` produce RGBA con alfa 0 en nodata
- [x] `registry` omite las capas declaradas que no existen en el disco
- [x] Conversión de lat/lon a fila/columna en esquinas y centro del bbox
- [x] Vitest: `layersPanel` crea un control por capa y cambia la opacidad

## Tests de integración

- [x] `/api/regions` incluye `jezero` con bbox válido
- [x] `/layers` devuelve 5 capas con todos los campos requeridos
- [x] `/image` devuelve `image/png` para cada capa
- [x] `/cell` dentro del bbox devuelve valores; fuera devuelve 422

## Tests de seguridad

- [x] Validación de inputs cubierta con test (lat/lon fuera de rango y
      `layer_id` inválido → 422)
- [x] Path traversal: `layer_id` = `..%2F..%2Fsecrets` → 404/422, sin leer
      fuera de `DATA_DIR`
- [x] Los errores no contienen stack trace ni rutas del disco
- [x] Control de acceso: endpoints públicos de solo lectura, documentado;
      no existe ningún endpoint de escritura
- [x] Test de aislamiento multi-tenant: no aplica en este proyecto (ver
      checklist 000, punto 3)
- [ ] Revisar contra `spec/features/000-seguridad-transversal/spec.md`
      antes de mergear
      <!-- falta: pasar el subagente auditor-seguridad -->

## E2E

- [x] Playwright: abrir la app → ver el mapa de Jezero → apagar y prender
      la capa de pendiente → bajar la opacidad → hacer clic en el centro →
      el popup muestra la pendiente en grados

---

*Al completar una tarea, márcala con `[x]`. Si surge una tarea nueva no
prevista, agrégala al final de su sección correspondiente en vez de
modificar las ya existentes. Si una tarea queda parcial, déjala en `[ ]`
con una nota `<!-- parcial: falta X -->`.*
