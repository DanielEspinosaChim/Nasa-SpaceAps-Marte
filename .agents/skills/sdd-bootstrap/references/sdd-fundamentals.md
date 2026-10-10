# Fundamentos de SDD — referencia de apoyo

Este archivo es material de consulta para usar durante la entrevista de
`sdd-bootstrap` o al redactar los archivos generados. No es necesario
leerlo entero de una vez; ve a la sección que necesites.

## El ciclo SDD

1. **Constitución** (una vez por proyecto): mission.md, tech-stack.md, roadmap.md.
2. **Specify**: qué se va a construir, con criterios de aceptación verificables.
3. **Plan**: cómo se va a construir — archivos exactos, endpoints, modelo de datos.
4. **Tasks**: el plan dividido en tareas pequeñas y verificables.
5. **Implement**: se ejecutan las tareas una a una.
6. **Verify**: se valida contra los criterios de aceptación; si falla, se ajusta.

El ciclo Specify → Plan → Tasks → Implement → Verify se repite en cada
feature nueva.

## Niveles de adopción

- **Spec-first**: la spec es el punto de partida; se genera el código una
  vez y luego se edita directo. Rápido, pero la spec se desactualiza.
- **Spec-anchored** (recomendado por default): la spec se mantiene viva —
  cada cambio importante pasa primero por actualizarla. Es el nivel que
  esta skill asume al generar el scaffold.
- **Spec-as-source**: la spec es lo único que se edita; el código se
  regenera siempre desde ella. Experimental, poco común todavía.

## Los 4 subagentes base

- **Coordinador**: no escribe código. Lee la tarea, la divide en
  subtareas y decide el orden y a qué subagente asignar cada una.
- **Implementador**: recibe una subtarea concreta y escribe el código.
  Puede haber varios en paralelo.
- **Tester**: corre y escribe tests (unit, integración, E2E). Valida que
  el resultado cumpla los criterios de aceptación de la spec
  correspondiente. No modifica código de producción, solo tests.
- **Auditor de seguridad**: acceso de solo lectura. Revisa inyecciones,
  manejo de secrets, validación de inputs, control de acceso y
  dependencias con CVEs conocidos.

Cada subagente devuelve solo un resumen de su trabajo al Coordinador —
nunca todo el detalle — para no saturar el contexto principal.

Subagentes adicionales comunes que el usuario puede pedir:
- **Auditor de performance**: cuellos de botella, queries lentas, uso de
  memoria. Solo lectura.
- **Documentador**: mantiene README y docs/ actualizados tras cada
  feature. Solo puede escribir en carpetas de documentación, no en código.

## Checklist de seguridad transversal (11 puntos)

Usar como base para `spec/features/000-seguridad-transversal/spec.md`:

1. Validación de todos los inputs de usuario (tipo, formato, longitud).
2. Control de acceso verificado en cada endpoint (autenticación +
   autorización, no solo autenticación).
3. Aislamiento multi-tenant: un usuario/cliente nunca puede leer o
   modificar datos de otro (si el proyecto maneja múltiples tenants).
4. Manejo de secrets: nada de credenciales, tokens o llaves hardcodeadas
   ni en el repo.
5. Protección contra inyecciones (SQL, NoSQL, comandos de sistema).
6. Protección contra XSS/CSRF en cualquier superficie web.
7. Límites de rate en endpoints públicos o sensibles.
8. Logging seguro: no se registran contraseñas, tokens ni datos
   personales sensibles en texto plano.
9. Manejo de errores que no filtra información interna (stack traces,
   rutas de archivo, versiones de librerías) al cliente.
10. Dependencias sin vulnerabilidades conocidas (CVEs) sin mitigar.
11. Subida de archivos (si aplica) validada por tipo real, tamaño máximo,
    y almacenada fuera de rutas ejecutables.

Si el proyecto no maneja tenants, el punto 3 se marca como "No aplica" en
el spec generado en vez de eliminarse — para que quede explícito que se
consideró.

## Revisión de spec antes de implementar

Antes de dar luz verde a implementar cualquier feature, se revisa que:

1. `spec.md` tenga al menos 5 criterios de aceptación verificables (no ambiguos).
2. `plan.md` liste archivos exactos a crear/modificar (no genéricos).
3. `plan.md` tenga los endpoints con método, path y descripción.
4. `plan.md` tenga el modelo de datos con campos y tipos.
5. `tasks.md` esté dividido en secciones con tareas atómicas.
6. `tasks.md` incluya al menos un test de aislamiento (multi-tenant si aplica).
7. No queden `<!-- REVISAR -->` sin resolver.

Si todo se cumple: **LISTO PARA IMPLEMENTAR**. Si no: se listan los puntos
faltantes y no se avanza a implementación.

## Texto recomendado para la sección "Flujo de trabajo" de CLAUDE.md

```
## Flujo de trabajo
- Para tareas grandes, refactors, o cambios que toquen más de 2 archivos:
  usa Plan Mode. Muestra el plan completo y espera mi OK explícito antes
  de tocar código.
- Para bugs evidentes, correcciones puntuales o tareas atómicas de un
  solo archivo: usa Build Mode y ejecuta directo.
- Una tarea a la vez; al terminar, dime qué cambiaste para que lo revise.
- Si no estás seguro al 80%, pregunta. No inventes.
```

## Loop engineering (para el bucle de verificación por feature)

Antes de cerrar una feature, se corre el bucle *Actuar → Observar →
Corregir* hasta que todos los tests pasen: el agente ejecuta, corre las
pruebas, si algo falla identifica la causa y corrige, y repite — sin
necesidad de que el humano supervise cada vuelta individual, solo el
resultado final.
