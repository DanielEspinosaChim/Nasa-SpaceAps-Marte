---
name: sdd-bootstrap
description: Use this skill whenever the user wants to set up a new software project (or retrofit an existing one) with Spec-Driven Development. It runs a conversational interview to define the mission, tech stack, roadmap, MCPs, subagents, security checklist and initial feature specs, then generates the complete file scaffold (spec/constitution/, CLAUDE.md, MCP config, subagent definitions, docs/, and spec/features/ for the first features). Trigger this whenever the user says things like "monta mi proyecto con SDD", "configúrame todo el flujo de agentes", "arranca un proyecto nuevo con specs", "hazme las preguntas para armar el proyecto", "quiero implementar spec-driven development", or when the user clearly wants Claude Code fully configured from zero but hasn't defined mission/roadmap/stack yet. Also use it mid-project if the user wants to add the harness, subagents, or security checklist they're missing.
---

# SDD Bootstrap — entrevista guiada + generación completa del scaffold

Esta skill convierte una plática con el usuario en el andamiaje completo de
Spec-Driven Development: constitución, arnés (CLAUDE.md), MCPs, subagentes,
checklist de seguridad y las primeras specs de feature — listo para empezar
a implementar.

No es un formulario. Es una conversación, un tema a la vez, con criterio
propio: si el usuario da una respuesta genérica, se le insiste con opciones
concretas antes de aceptarla.

## Principio central: entrevistar bien, no solo preguntar

- **Un tema a la vez.** Nunca sueltes las 7 preguntas juntas. Pregunta,
  espera la respuesta, reacciona en una línea, sigue.
- **No aceptes respuestas genéricas sin insistir.** Si el usuario dice "una
  app normal", "lo que tú creas mejor", "no sé, decide tú" en la primera
  pasada, no lo tomes como respuesta final. Ofrécele 2-4 opciones concretas
  construidas sobre lo que ya dijo, y pídele que elija o corrija. Solo si
  insiste en "decide tú" después de ver opciones concretas, usa un default
  razonable y márcalo con `<!-- REVISAR -->` en el archivo generado.
- **No inventes decisiones de negocio** (audiencia, monetización,
  cumplimiento normativo) sin confirmar. **Sí puedes proponer** decisiones
  técnicas concretas (stack, testing) porque son fáciles de corregir después
  — pero siempre como propuesta a confirmar, no como hecho consumado.
- **Cierra cada tema con un resumen de una línea** antes de pasar al
  siguiente, para que el usuario sienta que va avanzando y pueda corregir
  sobre la marcha.
- Si en cualquier momento el usuario pide saltarse pasos o ya trae la info
  lista (p. ej. pega su stack y roadmap de un jalón), no repitas preguntas
  que ya respondió — solo rellena huecos.

## Paso 0 — Detectar punto de partida

Pregunta primero: **¿Es un proyecto nuevo o ya existe código?**

- **Si ya existe código:** antes de preguntar nada más, lee tú mismo el
  repo (package.json / requirements.txt / pyproject.toml / README / entry
  points principales). Infiere stack, estructura y de qué trata el
  proyecto. Preséntale al usuario lo que dedujiste ("Veo que es un backend
  en FastAPI con PostgreSQL, ¿es correcto?") y solo pregunta lo que no
  pudiste inferir (misión real, roadmap futuro, subagentes deseados).
- **Si es nuevo:** sigue la entrevista completa de abajo, en orden.

## Paso 1 — Misión

Pregunta: *"¿Qué vas a construir y para quién? Cuéntamelo como si se lo
explicaras a un amigo, no hace falta que esté pulido."*

- Si la respuesta es vaga ("una plataforma para gestionar cosas"), no la
  aceptes: ofrece opciones concretas, ej. *"¿Es más parecido a (A) un
  gestor de tareas interno para tu equipo, (B) una plataforma para
  clientes externos, (C) una herramienta de datos/reportes, o (D) otra
  cosa muy distinta?"*
- Pregunta de seguimiento hasta tener: **qué es**, **para quién** (usuario
  final), **qué problema le resuelve**, y si aplica, **qué lo hace
  distinto**.
- Cierra con un resumen de una frase y pasa al siguiente tema.

## Paso 2 — Tech stack

Pregunta: *"¿Ya tienes el stack decidido, o quieres que te proponga uno
según lo que me describiste?"*

- Si ya lo tiene: captura lenguaje, framework/runtime, base de datos,
  framework de tests.
- Si no lo tiene: **propón un stack concreto** (no una lista genérica de
  opciones) basado en la misión, y pide confirmación. Ej.: *"Para esto te
  propondría TypeScript + Next.js + PostgreSQL (Prisma) + Vitest. ¿Te
  sirve o prefieres otra cosa (Python/FastAPI, otro frontend, etc.)?"*
- Nunca dejes el tech-stack.md final con placeholders sin rellenar —
  o hay una decisión real, o hay un `<!-- REVISAR -->` explícito.

## Paso 3 — Roadmap

Pregunta: *"Dime todas las funcionalidades que se te ocurran, sin orden ni
filtro — un brain dump. Yo las organizo después."*

- Tú te encargas de **ordenarlas** en una secuencia lógica de construcción
  (lo que otras features dependen va primero; MVP antes que
  nice-to-haves). Muéstrale el roadmap ya ordenado antes de escribir el
  archivo, y pide su OK o ajustes.
- Si la lista que da es muy corta (1-2 items) para la misión que describió,
  **sugiere proactivamente 3-5 features típicas** de un proyecto así,
  claramente marcadas como sugerencia tuya, y pregunta cuáles incluir. No
  dejes que el roadmap quede incompleto por falta de iniciativa tuya.

## Paso 4 — MCPs

Pregunta: *"¿Configuro Context7 para tener siempre documentación
actualizada? Te lo recomiendo por default."* Después: *"¿Necesitas algún
otro MCP — GitHub, base de datos, Figma, Slack, etc.? Dime cuáles o dime
que por ahora no."*

- Solo configura lo que el usuario confirme explícitamente. No instales
  MCPs de forma especulativa "por si acaso".
- Antes de escribir la configuración real de cada MCP, verifica la sintaxis
  actual (documentación del MCP, o `docs.claude.com`) en vez de asumirla de
  memoria — el formato de configuración cambia entre herramientas y
  versiones.

## Paso 5 — Subagentes

Explica en una línea los 4 roles base (Coordinador, Implementador, Tester,
Auditor de seguridad — ver `references/sdd-fundamentals.md` si necesitas
recordar sus responsabilidades exactas) y pregunta: *"¿Te sirven estos 4 o
quieres agregar/quitar alguno (ej. Auditor de performance, Documentador,
Diseñador de UI)?"*

- Para cualquier subagente adicional que pida, exige especificidad: **qué
  hace exactamente**, **qué permisos tiene** (solo lectura / lectura y
  escritura), **a qué archivos o carpetas puede tocar**. No aceptes "que
  revise el código" sin acotar — pide una responsabilidad concreta y
  acotada, igual que los 4 roles base.

## Paso 6 — Checklist de seguridad transversal

Avísale que vas a crear un checklist estándar de 11 puntos (validación de
inputs, control de acceso, manejo de secrets, protección contra
inyecciones, límites de rate, logging seguro, etc. — ver referencia) y
solo pregunta: *"¿Tu proyecto maneja datos de múltiples clientes/tenants
que deban estar aislados entre sí?"* (afecta un punto específico del
checklist). No conviertas esto en una entrevista larga — es mayormente
estándar.

## Paso 7 — Features con las que arrancar

Pregunta: *"De tu roadmap, ¿con cuántas features quieres que te arme ya el
spec completo (spec.md + plan.md + tasks.md) para poder implementarlas de
una vez? Te recomiendo empezar con 1 a 3."*

- Para cada feature seleccionada, aclara rápido: **qué módulos toca**
  (backend/frontend/ambos), **de qué depende**, **qué queda fuera de
  alcance**. Sé ágil aquí — no vuelvas a discutir el roadmap completo, solo
  aterriza estos 3 datos por feature.

## Paso 8 — Recapitulación final antes de tocar disco

Muestra un resumen compacto de todo lo capturado: misión en una frase,
stack, roadmap ordenado, MCPs a configurar, subagentes definidos, features
a generar con spec completo. Pregunta explícitamente si procede con la
generación de archivos antes de crear nada.

En este mismo paso, pregunta una sola vez: *"¿Hay alguna regla de 'no
hagas' específica que quieras además de las estándar (no borrar sin
avisar, no subir secrets, no instalar dependencias sin avisar)? Por
ejemplo, carpetas legacy que no debo tocar."*

## Generar los archivos

Con la confirmación del paso 8, crea esta estructura. Usa las plantillas
de `assets/` como base para cada archivo — rellénalas por completo con lo
que salió de la entrevista. Nunca dejes placeholders entre corchetes sin
resolver; usa `<!-- REVISAR -->` únicamente para lo genuinamente pendiente.

```
spec/
├── constitution/
│   ├── mission.md
│   ├── tech-stack.md
│   └── roadmap.md
└── features/
    ├── 000-seguridad-transversal/
    │   └── spec.md
    ├── 001-[feature]/
    │   ├── spec.md
    │   ├── plan.md
    │   └── tasks.md
    └── 00N-[feature]/...
CLAUDE.md
docs/
└── README.md   (regla de auto-actualización + formato de notas de sesión)
```

Además:

1. **CLAUDE.md** — usa `assets/CLAUDE.md.template`, rellenado por
   completo: stack real, comandos reales (si el proyecto ya existe;
   propuestos y marcados si es nuevo), estructura, convenciones, la
   sección "No hagas" (estándar + lo que el usuario haya pedido en el
   paso 8), y el flujo de trabajo con la regla de Build vs Plan Mode ya
   redactada explícitamente (ver `references/sdd-fundamentals.md` si
   necesitas el texto exacto recomendado). **Incluye también, sin
   excepción, la regla de auto-actualización de `docs/`** que ya trae el
   template — no la resumas ni la quites: es lo que hace que la memoria de
   sesión se mantenga sola en el tiempo, no solo al crearse.
2. **MCPs** — escribe la configuración real de cada MCP confirmado en el
   paso 4, verificando la sintaxis vigente en vez de asumirla.
3. **Subagentes** — escribe la definición de cada subagente confirmado en
   el paso 5, usando el mecanismo de configuración de subagentes vigente
   en Claude Code (verifica la sintaxis actual en vez de asumirla).
4. **spec/features/000-seguridad-transversal/spec.md** — usa
   `assets/security-checklist.md.template`, ajustando el punto de
   aislamiento multi-tenant según la respuesta del paso 6.
5. **Cada feature seleccionada en el paso 7** — usa
   `assets/spec.md.template`, `assets/plan.md.template` y
   `assets/tasks.md.template`, incluyendo en `tasks.md` los checks de
   seguridad transversal como indica el propio template.
6. **docs/README.md** — usa `assets/docs-README.md.template` tal cual;
   este archivo es lo que le recuerda al agente, en cualquier sesión
   futura, que `docs/` se actualiza solo sin que el usuario lo pida.

## docs/ no es un paso único — es una regla permanente

A diferencia de la constitución (que se escribe una vez), `docs/` **se
actualiza en cada sesión de trabajo relevante durante toda la vida del
proyecto**, automáticamente, porque así quedó escrito en `CLAUDE.md`. Esta
skill solo se encarga de dejar la regla y la carpeta listas — a partir de
ahí, es el propio agente (guiado por su CLAUDE.md) quien mantiene `docs/`
al día en cada sesión futura, sin que esta skill vuelva a intervenir.

Si en algún momento notas que `docs/` no se está actualizando solo (el
agente no la revisó al empezar una tarea, o no dejó nota al cerrar una),
es una señal de que `CLAUDE.md` se está ignorando — recuérdaselo al
usuario en vez de simplemente seguir sin documentar.

## Después de generar

- Imprime el árbol de archivos final que quedó creado.
- Recuerda al usuario el siguiente paso inmediato: revisar que cada spec
  recién creada diga "LISTO PARA IMPLEMENTAR" antes de empezar a
  implementar (ver `references/sdd-fundamentals.md`, sección de revisión
  de spec).
- **No empieces a implementar código de ninguna feature todavía** — el
  trabajo de esta skill termina en el andamiaje, no en la construcción.

## Referencia

`references/sdd-fundamentals.md` contiene el ciclo SDD completo, los
niveles de adopción, el detalle de los 4 subagentes base, el checklist de
seguridad de 11 puntos y los prompts de verificación de spec. Consúltalo
cuando necesites explicarle algo al usuario durante la entrevista o cuando
un archivo generado necesite más contenido del que cabe en la plantilla.
