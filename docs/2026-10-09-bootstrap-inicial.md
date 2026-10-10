# 2026-10-09 — Bootstrap inicial del proyecto con Spec-Driven Development

## Qué se hizo

1. **Debate y alineación conceptual**:
   - Se resolvió la naturaleza del robot: un rover explorador simulado que propone, planifica, visita y reporta para entregar un mapa por capas mejorado a astronautas/planificadores de misión.
   - Se delimitó la tecnología: A\* para tramos óptimos punto a punto; algoritmo genético multiobjetivo (NSGA-II) para selección y orden de misiones (problema de orienteering bajo restricciones de energía, walkback 10 km y zonas prohibidas); dos niveles de percepción (mapas orbitales previos de NASA + verdad en suelo con sensores y CNNs locales).
   - Región elegida para demostración: Cráter Jezero (+18.4° N, 77.5° E).

2. **Andamiaje SDD completado**:
   - `spec/constitution/`: `mission.md`, `tech-stack.md` y `roadmap.md` (12 features ordenadas de la más fundacional a la más opcional).
   - `spec/features/000-seguridad-transversal/spec.md`: checklist de 11 puntos adaptado a demo pública de computación geoespacial.
   - Especificaciones completas listas para las 3 primeras features del MVP (`spec.md`, `plan.md`, `tasks.md`):
     - `001-pipeline-terreno` (generación de DEM, pendiente, rugosidad, hillshade, transitabilidad, soporte sintético).
     - `002-mapa-capas-web` (FastAPI + MapLibre GL JS, visualización de capas, opacidad, consulta de celda).
     - `003-planificador-a-estrella` (costmap, A\*, Dijkstra de referencia, restricciones duras, perfiles y explicaciones).
   - Configuración de agente y harness:
     - `CLAUDE.md` y `AGENTS.md` con reglas de operación, flujo de trabajo, convenciones marcianas y no-hagas.
     - `.mcp.json` configurado con Context7 para documentación al día.
     - 5 subagentes definidos en `.claude/agents/`: Coordinador, Implementador, Tester, Auditor de seguridad y Validador científico.
     - `.env.example`, `.gitignore` y regla persistente en `docs/README.md`.

## Qué quedó pendiente

- Validación del equipo sobre las primeras 3 specs para marcarlas formalmente como `LISTO PARA IMPLEMENTAR`.
- Arranque de la implementación de la **Feature 001 (Pipeline de terreno)**: creación de `pyproject.toml`, entorno virtual e implementación del pipeline matemático con terreno sintético reproducible.
- Cuando el usuario comparta los archivos/enlaces de los datasets de NASA descargados, colocarlos en `data/raw/` o configurar su descarga.

## Decisiones tomadas

- **D1**: El robot es un rover de navegación sobre terreno (sin cinemática física compleja de patas).
- **D2**: Separación estricta A\* (geometría de ruta local) vs. Genético (estrategia global multiobjetivo).
- **D3**: El dataset sintético determinista (--seed) es el estándar de desarrollo y testing para no bloquearse por la falta de red o de archivos PDS pesados.
