# Registro de decisiones — Martian Map (NASA Space Apps 2026)

Reto: *Interplanetary Survival Guide: Martian Map* — vista integrada y por capas de una ruta/ubicación en Marte con datos de varias misiones NASA.

## Decisiones cerradas

### D1 — Qué es el robot
Rover (carrito) simulado que se mueve sobre el terreno. **Propone, planifica, visita y reporta** zonas de interés.
Se modela como **navegación sobre terreno** (sin patas ni física de articulaciones).

### D2 — Rol de cada algoritmo
- **A\***: calcula los tramos óptimos entre dos puntos sobre el mapa de costos.
- **Algoritmo genético multiobjetivo (NSGA-II)**: decide la misión — qué zonas visitar, en qué orden y cuáles descartar — bajo restricciones (energía, walkback 10 km, zonas prohibidas).
- **Switch de modelos**: el GA produce un frente de Pareto (misiones segura / rápida / científica y sus balances). Los sliders del panel eligen un punto de ese frente.

### D2b — Dos niveles de información
| Nivel | Fuente | Rol |
|---|---|---|
| Mapa previo | Satélites NASA existentes (MRO: HiRISE, CTX; MOLA; CRISM) | Planeación estratégica |
| Verdad en suelo | Sensores del robot (cámara + CNN) | Confirmar, descubrir peligros ocultos, replanificar |

Flujo: cargar mapa → GA planifica → robot visita y verifica → **actualiza el mapa** para astronautas.

### Región tentativa
Cráter **Jezero** (18.4° N, 77.5° E). Validación: comparar contra la ruta real de Perseverance.

### D8 — El genético corre en CPU, no en GPU
Medido el 2026-10-09: 15 POI sobre ~300×270 celdas, matriz de tramos + NSGA-II (100×200) en
1.3–2.3 s. El costo está en evaluar secuencias cortas (≤ 8 paradas, con caché) y en Dijkstra
sobre un grafo disperso, que no se paralelizan en GPU; pasar datos a la GPU lo haría más lento.
La GPU (RTX 5060 Laptop, 8 GB) se reserva para PyTorch en 007 y 008. Se reconsidera si el
problema crece a cientos de POI.

### D9 — Control de calidad del genético
10/10 semillas igualan a la fuerza bruta con 7 POI y el hipervolumen supera al greedy en las 5
semillas con 15 POI (tests `tests/planning/mission/test_quality.py`).

### D10 — Puntos de interés = sitios de muestras reales de Mars 2020
Sustituye a los puntos ilustrativos. Fuente: capa «Sampling Locations» de NASA/JPL (22 sitios hasta
el sol 1483). Hábitat por defecto = aterrizaje publicado por NASA (waypoint sol 13). El valor
científico es una **rúbrica del proyecto** (tipo de muestra + litología), no un dato de NASA; debe
presentarse así. Con el walkback de 10 km, 17 sitios entran y 5 (borde del cráter, Witch Hazel Hill)
se descartan de forma natural.

## Pendientes
- D3 — Qué ve la cámara del robot y qué cuenta como "interesante".
- D4 — Recolección de muestras / umbrales para "traer" objetos.
- D5 — Función de aptitud final. **Propuesta en `spec/features/004-mision-genetica-nsga2/`** (pendiente de confirmar con el equipo):
  - Objetivos: maximizar ciencia, minimizar tiempo, minimizar riesgo (metros en terreno de riesgo + penalización por pendiente > 10°).
  - Restricciones duras: energía ≤ presupuesto, tiempo ≤ máximo, sin tramos bloqueados, walkback 10 km, zonas prohibidas, salida y regreso al hábitat.
  - Los sliders (005) usan seguridad/ciencia/velocidad como pesos sobre el frente de Pareto; energía actúa como presupuesto (restricción), no como objetivo.
- D6 — Métricas de evaluación y baseline.
- D7 — Stack y reparto del equipo.
