# Roadmap

Orden de construcción de las features, de la más fundacional a la más
opcional. Los números de feature (00X) corresponden a las carpetas en
`spec/features/`.

## MVP — construir primero

1. **001-pipeline-terreno**: descarga y recorta el DEM de Jezero y calcula
   pendiente, rugosidad, sombreado y transitabilidad. Todo lo demás depende de
   estas capas. Incluye un generador de terreno sintético para trabajar
   offline.
2. **002-mapa-capas-web**: API FastAPI más mapa MapLibre por capas, con
   leyenda, opacidad, fuentes y consulta de celda. Es la vista que pide el
   reto y la base visual de todo lo demás.
3. **003-planificador-a-estrella**: mapa de costos con restricciones duras
   y A\* entre dos puntos, con métricas, perfil altimétrico y explicación de
   la ruta. Es la pieza que usa el genético para medir tramos.
4. **004-mision-genetica-nsga2**: el genético multiobjetivo decide qué
   zonas de interés visitar y en qué orden (energía, walkback de 10 km, zonas
   prohibidas) y genera un frente de Pareto.
5. **005-panel-calibracion**: sliders de seguridad, ciencia, velocidad y
   energía que eligen un punto del frente de Pareto (el "switch de
   modelos") y muestran la misión resultante.

## Siguiente etapa

6. **006-simulacion-rover**: el rover recorre la misión paso a paso. Una
   capa oculta de "verdad en suelo" con peligros no visibles desde órbita se
   revela en un radio de sensado, y el rover replanifica.
7. **007-vision-terreno-ai4mars**: CNN que clasifica suelo, roca madre,
   arena y roca grande, entrenada con AI4Mars. Alimenta la seguridad local
   del rover.
8. **008-detector-novedad**: autoencoder que marca lo "fuera de lo común"
   como interesante, sin etiquetas.
9. **009-actualizacion-mapa**: lo que descubre el rover actualiza las
   capas, se marca la diferencia entre el mapa orbital y el mapa verificado,
   y se genera un reporte para astronautas.
10. **010-evaluacion-baseline**: métricas contra A\*/Dijkstra exacto y
    comparación con la ruta real de Perseverance (SPICE o traverse
    publicado).
11. **011-capas-ciencia**: puntos de interés científico (CRISM, objetivos
    de Mars 2020) como beneficio en la función de aptitud.
12. **012-recoleccion-muestras**: umbrales y métricas para que el rover
    decida "traer" una muestra (puntaje de interés frente a costo de
    energía y capacidad). Los umbrales se definen al escribir la spec de la
    012 (decisión D4, pendiente en `docs/decisiones.md`).

## Backlog / ideas futuras (sin priorizar todavía)

- Vista 3D del relieve con CesiumJS.
- Capa ambiental con datos históricos de InSight (solo contexto).
- Capa de radiación (RAD, Curiosity) y refugios (pozos o fosas con búfer).
- Proximidad a hielo subsuperficial (mapas SWIM) como beneficio.
- Iluminación y sombras calculadas desde el DEM para energía solar.
- Zonas prohibidas por protección planetaria (RSL con búfer de 50 km, según
  el MEPAG) como restricción dura configurable.
- Comparación del genético contra RL (PPO) para la política local.
- Modo de reemplazo rápido de datos cuando NASA publique los datasets
  oficiales del reto.

---

*Este roadmap se ajusta con el tiempo. Antes de reordenar prioridades,
actualízalo aquí primero.*
