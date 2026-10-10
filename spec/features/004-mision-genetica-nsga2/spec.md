# Spec — 004 Misión genética (NSGA-II)

**Estado: LISTO PARA IMPLEMENTAR** (revisado el 2026-10-09)

## Qué hace

Decide la **misión** del rover: qué puntos de interés (POI) visitar, en qué
orden y cuáles descartar, saliendo del hábitat y volviendo a él. Respeta
restricciones duras: presupuesto de energía, tiempo máximo, walkback de
10 km y zonas prohibidas. Un **algoritmo genético multiobjetivo (NSGA-II)**
optimiza tres objetivos a la vez: **maximizar el valor científico**,
**minimizar el tiempo** y **minimizar el riesgo**. Devuelve un **frente de
Pareto** de misiones, no una sola. Cada misión trae geometría, métricas y
una explicación de por qué visita cada punto y por qué descarta los demás.
Los tramos entre puntos los calcula el mapa de costos de la 003 (decisión
D2: A\* hace los tramos, el genético hace la misión).

Cuatro misiones del frente tienen nombre: **segura**, **rápida**,
**científica** y **balanceada**. Además, `select_mission(front, weights)`
elige un punto del frente a partir de pesos. Esa función es la base del
"switch de modelos" que usarán los sliders de la 005.

## Módulos que toca

- [x] Backend (`marsmap.planning.mission`, endpoint de misión)
- [x] Frontend (botón de planificar, misión con paradas numeradas y
      descartes)

## Depende de

- 001-pipeline-terreno (capas).
- 002-mapa-capas-web (API base, registro de regiones y mapa).
- 003-planificador-a-estrella (mapa de costos, restricciones,
  `poi.geojson`, métricas y explicaciones de tramo).

## Fuera de alcance

- Sliders de calibración y gráfico del frente de Pareto (005). Aquí solo
  hay botones para las cuatro misiones con nombre.
- Recorrer la misión paso a paso y replanificar ante peligros ocultos
  (006).
- Valor científico calculado desde CRISM u otros datos (011). En esta
  feature, `science_value` viene asignado a mano en `poi.geojson`, con su
  justificación.
- Recolección de muestras y capacidad de carga (012).
- Comparar contra RL (backlog).

## Criterios de aceptación

1. **Matriz de tramos**: para el hábitat más N POI, se calcula una matriz
   (N+1)×(N+1) con `cost`, `distance_m`, `time_h`, `energy_wh`,
   `risk_m` y `max_slope_deg` de cada tramo. Usa una búsqueda de una sola
   fuente por nodo sobre el mismo grafo de la 003. En 10 pares aleatorios
   de un mapa sintético, el costo del tramo es igual (± 1e-6) al de A\* de
   la 003.
2. **Restricciones duras**: ninguna misión del frente supera
   `energy_budget_wh` ni `max_time_h`. Ningún tramo pasa por celdas
   bloqueadas, por zonas prohibidas ni fuera de `max_radius_m` desde el
   hábitat. Toda misión empieza y termina en el hábitat. Un test sobre 10
   semillas da 0 violaciones.
3. **Descartes previos**: los POI fuera del radio de walkback, dentro de
   una zona prohibida o sin tramo posible desde el hábitat se excluyen antes
   de optimizar. Aparecen en `discarded` con un `reason_code`
   (`outside_walkback`, `forbidden_zone`, `unreachable`) y un texto legible.
4. **Calidad contra la solución exacta**: con 7 POI sintéticos, la fuerza
   bruta (todas las combinaciones y órdenes posibles) da la misión de mayor
   valor científico que cumple las restricciones. En al menos 9 de 10
   semillas, la misión `science` del frente tiene el mismo valor científico
   (± 1e-6). En las demás, queda dentro del 5%.
5. **Mejor que el baseline greedy**: con 15 POI sintéticos, el hipervolumen
   del frente de NSGA-II es mayor o igual que el del conjunto de misiones
   del greedy (siempre visitar el POI con más ciencia por unidad de costo),
   en las 5 semillas de prueba.
6. **Frente válido**: todas las misiones devueltas son no dominadas entre
   sí en (−ciencia, tiempo, riesgo). El frente tiene entre 1 y
   `max_front_size` misiones (por defecto 30), sin duplicados de
   secuencia.
7. **Misiones con nombre**: `safe` es la de menor `risk_score` (metros en terreno de riesgo más
   penalización por pendiente máxima), `fast` la de
   menor `time_h` entre las que visitan al menos 1 POI, `science` la de
   mayor `science_total` y `balanced` el punto de rodilla (la más cercana
   al punto ideal con objetivos normalizados a [0,1]). Si el frente tiene
   una sola misión, las cuatro apuntan a ella.
8. **Selector**: `select_mission(front, weights)` con
   `weights = {safety, science, speed}` (cada uno en [0,1], no todos 0)
   devuelve la misión que minimiza la suma ponderada de los objetivos
   normalizados. Con `{safety:1, science:0, speed:0}` coincide con `safe`;
   con `{0,1,0}`, con `science`; con `{0,0,1}`, con `fast`.
9. **Determinismo**: la misma semilla y los mismos parámetros producen el
   mismo frente, con iguales secuencias y objetivos.
10. **Explicaciones**: cada misión trae al menos una explicación por POI
    visitado y una por POI descartado, con cifras concretas. Ejemplos:
    "Visita el delta occidental (ciencia 0.9) antes que el borde del cráter:
    ese orden ahorra 1.4 km" o "Descarta la duna norte: costaría 380 Wh por
    0.2 de ciencia y la batería no alcanza".
11. **Rendimiento**: con 15 POI en una cuadrícula de 300×300, la matriz de
    tramos más la optimización (población de 100, 200 generaciones) tardan
    menos de 20 s en una laptop normal.
12. En el frontend, al pulsar "Planificar misión" se dibuja la misión
    `balanced` con paradas numeradas y tramos coloreados por riesgo. Los
    botones "segura", "rápida", "científica" y "balanceada" cambian la
    misión mostrada sin volver a calcular, y se listan los POI descartados
    con su razón.
