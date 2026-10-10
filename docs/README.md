# Memoria de sesión del proyecto

Esta carpeta es la memoria persistente del agente entre sesiones. **Se
actualiza sola** — no hace falta pedírselo cada vez, es una regla fija en
`CLAUDE.md` (sección "Flujo de trabajo").

## Regla de actualización automática

Al cerrar cualquier tarea o sesión de trabajo relevante (no cada micro-
cambio, sino cada bloque de trabajo con sentido propio), el agente crea o
actualiza una entrada aquí con:

- **Fecha**
- **Qué se hizo**
- **Qué quedó pendiente**
- **Decisiones tomadas** (y por qué, si no es obvio)

Antes de empezar una tarea nueva, el agente revisa esta carpeta primero.
Si el contexto ya está documentado aquí, no debe volver a preguntarlo.

## Formato sugerido por entrada

Un archivo por sesión o por bloque de trabajo, nombrado por fecha:

```
docs/
├── README.md              (este archivo)
├── 2026-10-09-bootstrap-inicial.md
└── ...
```

## Por qué existe esta carpeta

Permite "particionar el cerebro" del agente: retomar el contexto de una
tarea específica semanas después sin tener que releer todo el historial
de chat ni saturar la ventana de contexto.
