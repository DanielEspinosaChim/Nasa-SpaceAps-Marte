# Spec — 003 Planificador A\*

**Estado: LISTO PARA IMPLEMENTAR** (revisado el 2026-10-09)

## Qué hace

Construye un **mapa de costos** a partir de las capas de terreno (pendiente,
rugosidad y transitabilidad) con pesos configurables y **restricciones
duras**: celdas bloqueadas, zonas prohibidas y radio máximo desde el
hábitat. Sobre ese mapa calcula con **A\*** la ruta óptima entre dos puntos.
Devuelve la ruta como GeoJSON con métricas, perfil altimétrico y una
**explicación en lenguaje natural** de por qué se eligió. Es el motor de
tramos que usará el genético (004) y ya ofrece las tres rutas que pide la
guía: segura, rápida y científica (esta última con un beneficio simple por
puntos de interés).

## Módulos que toca

- [x] Backend (`marsmap.planning`, endpoint de ruta)
- [x] Frontend (selección de inicio y destino, dibujo de ruta y perfil)

## Depende de

- 001-pipeline-terreno (capas).
- 002-mapa-capas-web (API base, registro y mapa).

## Fuera de alcance

- Visitar varios puntos de interés con orden óptimo (eso es el genético,
  004).
- Sliders de calibración completos (005). Aquí solo hay tres presets de
  pesos.
- Peligros ocultos y replanificación en simulación (006).
- Costo energético físico detallado del rover. Se usa una aproximación por
  distancia 3D y pendiente.

## Criterios de aceptación

1. En un mapa sintético con un "muro" de celdas bloqueadas y un solo hueco,
   la ruta pasa por el hueco.
2. **Optimalidad**: en 20 mapas sintéticos aleatorios de 50×50 (semillas
   fijas), el costo de la ruta de A\* es igual (± 1e-6) al de un Dijkstra de
   referencia sobre el mismo grafo.
3. **Restricciones duras**: ninguna ruta devuelta pasa por celdas con
   transitabilidad `2` (> 15°), por celdas dentro de zonas prohibidas
   (incluido su búfer) ni por celdas fuera del radio máximo desde el hábitat
   si este se especifica. Un test sobre 100 rutas aleatorias da 0
   violaciones.
4. Si el inicio o el destino están en una celda bloqueada, prohibida o fuera
   de la región, responde 422 con un `code` específico
   (`start_blocked`, `goal_blocked`, `out_of_region`).
5. Si no existe ruta, responde 200 con `status: "no_route"` y un
   `reason` legible.
6. La respuesta incluye `status`, `geometry` (GeoJSON LineString),
   `distance_m` (3D), `straight_line_m`, `tortuosity`
   (= distance / straight_line), `max_slope_deg`, `mean_slope_deg`,
   `elevation_gain_m`, `elevation_loss_m`, `pct_risk_cells`,
   `est_time_h`, `profile` (lista de distancia acumulada y elevación),
   `explanations` y `compute_ms`.
7. **Presets**: sobre 30 rutas aleatorias en un mapa sintético, el
   `max_slope_deg` medio de `safe` es ≤ al de `fast` y el `distance_m` medio
   de `fast` es ≤ al de `safe`; además, cada desigualdad se cumple en al
   menos el 80% de las rutas individuales. (Minimizar un costo ponderado no
   garantiza el orden en cada ruta, por eso se mide en agregado.)
8. Cada ruta trae al menos una explicación con cifras concretas, generada
   comparando contra la línea recta, por ejemplo "Evita una zona con
   pendiente de 19° al norte (+1.2 km de desvío)" o "El 92% del recorrido
   está en terreno seguro".
9. **Rendimiento**: una ruta en una cuadrícula de 300×300 se calcula en
   menos de 2 s.
10. En el frontend, al hacer clic en "inicio" y "destino" y elegir un
    preset, se dibuja la ruta, se muestran las métricas y el perfil
    altimétrico, y se listan las explicaciones.
