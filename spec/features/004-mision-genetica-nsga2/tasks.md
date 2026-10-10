# Tasks — 004 Misión genética (NSGA-II)

Checklist de tareas atómicas y verificables. Marcar `[x]` solo cuando esté
implementado Y verificado, no solo escrito.

## Backend

- [x] Agregar pymoo a `pyproject.toml`
- [x] Crear `mission_config.yaml` con el modelo de energía, los límites y
      los parámetros del genético
- [x] Implementar `poi.py` (modelo `PointOfInterest` y carga de GeoJSON
      con normalización de longitud)
- [x] Agregar `generate_pois(bbox, n, seed)` a `terrain/synthetic.py`
- [x] Implementar `prefilter.py` (`outside_walkback` y `forbidden_zone`)
- [x] Implementar `legs.py`: grafo disperso de 8 vecinos desde el mapa de
      costos de la 003
- [x] Implementar `legs.py`: Dijkstra multi-fuente, reconstrucción de
      tramos y métricas por tramo
- [x] Implementar `energy.py`
- [x] Implementar `encoding.py`: decodificación de claves aleatorias y
      2-opt
- [x] Implementar `problem.py` (`MissionProblem` con 3 objetivos y 3
      restricciones, vectorizado)
- [x] Implementar `optimize.py` (NSGA-II, no dominados, duplicados y
      recorte por crowding)
- [x] Implementar `select.py` (misiones con nombre y `select_mission`)
- [x] Implementar `explain.py` (visitados, descartados en la optimización
      y descartados antes de optimizar)
- [x] Implementar `baselines/bruteforce.py` y `baselines/greedy.py`
- [x] Implementar `GET /pois`, `POST /missions` y `POST /missions/{id}/select`
      con caché LRU y rate limit
- [x] Ampliar `poi.geojson` de Jezero con sitios reales: 22 sitios de muestras de Mars 2020 (NASA/JPL),
      con `science_value` por rúbrica del proyecto (ver data/README.md)

## Frontend

- [x] `missionPlanner.js`: elegir el hábitat en el mapa y el botón
      "Planificar misión" con estado de carga
- [x] Botones de las misiones con nombre (segura, rápida, científica y
      balanceada) sin volver a calcular
- [x] `missionLayer.js`: tramos coloreados por riesgo y marcadores
      numerados por orden de visita
- [x] Dibujar el círculo de walkback de 10 km alrededor del hábitat
- [x] `missionReport.js`: métricas (ciencia, tiempo, energía y riesgo),
      explicaciones y descartes con `textContent`
- [x] Mostrar errores 422/429 y el timeout de forma clara

## Tests unitarios

- [x] Tramos: el costo de la matriz es igual al de A\* de la 003 (± 1e-6)
      en 10 pares aleatorios
- [x] Decodificación: claves conocidas producen la secuencia esperada; con
      todas < 0.5 sale la misión vacía
- [x] 2-opt: nunca empeora el tiempo de la secuencia de entrada
- [x] Prefiltro: un POI a 10.5 km del hábitat sale como `outside_walkback`
      y uno dentro de una zona, como `forbidden_zone`
- [x] Restricciones: 0 violaciones de energía, tiempo, bloqueo, zonas o
      radio en 10 semillas
- [x] Frente: todas las misiones son no dominadas entre sí y sin
      secuencias duplicadas
- [x] Misiones con nombre: cada una es el extremo correcto; con frente de
      tamaño 1, las cuatro coinciden
- [x] Selector: pesos puros devuelven `safe`, `science` y `fast`;
      pesos todos en 0 se rechazan
- [x] Determinismo: la misma semilla da el mismo frente
- [x] Explicaciones: ≥ 1 por POI visitado y descartado, y todas con al
      menos un número

## Tests de integración

- [x] Calidad: con 7 POI, la misión `science` iguala a la fuerza bruta en
      ≥ 9 de 10 semillas (el resto, dentro del 5%)
- [x] Calidad: con 15 POI, el hipervolumen de NSGA-II ≥ el del greedy en 5
      semillas
- [x] `POST /missions` con terreno y POI sintéticos devuelve 200 con todos
      los campos de `MissionResultOut`
- [x] `POST /missions/{id}/select` devuelve una misión del frente; con un
      `result_id` desconocido, 404 `result_expired`
- [x] Hábitat en una celda bloqueada → 422 `habitat_blocked`
- [x] Rendimiento: 15 POI en 300×300 en menos de 20 s

## Tests de seguridad

- [x] Validación de inputs cubierta con test (`pop_size`,
      `n_generations`, presupuesto o radio fuera de rango, más de 20
      `poi_ids` o un `poi_id` con `../` → 422)
- [x] Rate limit: exceder el límite de `/missions` devuelve 429
- [x] Timeout: con parámetros máximos, la respuesta es controlada y no
      cuelga el servidor
- [x] Caché: muchas peticiones con parámetros distintos no superan el
      tamaño máximo de la LRU
- [x] Control de acceso: endpoint público de cómputo sin escritura
      persistente, documentado
- [x] Test de aislamiento multi-tenant: no aplica en este proyecto (ver
      checklist 000, punto 3)
- [ ] Revisar contra `spec/features/000-seguridad-transversal/spec.md`
      antes de mergear
      <!-- falta: pasar el subagente auditor-seguridad -->

## E2E

- [x] Playwright: abrir el mapa → elegir el hábitat en Jezero →
      "Planificar misión" → se dibuja la misión balanceada con paradas
      numeradas → cambiar a "científica" → la ciencia mostrada es mayor o
      igual → se ve la lista de descartes con su razón

---

*Al completar una tarea, márcala con `[x]`. Si surge una tarea nueva no
prevista, agrégala al final de su sección correspondiente en vez de
modificar las ya existentes. Si una tarea queda parcial, déjala en `[ ]`
con una nota `<!-- parcial: falta X -->`.*
