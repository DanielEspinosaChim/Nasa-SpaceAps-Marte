# Misión

Proyecto para el reto **"Interplanetary Survival Guide: Martian Map"** del
NASA Space Apps Challenge 2026: crear una vista integrada y por capas de una
ubicación o ruta en la superficie de Marte, combinando datos de varias
misiones científicas de NASA, que ayude a una persona exploradora a planear
y ejecutar su misión de forma rápida y segura.

## Qué construimos

**Mars Scout**: un rover
autónomo simulado que usa el mapa satelital existente de NASA (MOLA, HRSC,
CTX, HiRISE, CRISM) para **proponer, planificar, visitar y reportar** zonas de
interés en Marte. Un algoritmo genético multiobjetivo decide qué zonas visitar
y en qué orden; A\* calcula los tramos entre ellas. El rover recorre la misión
en simulación, verifica el terreno con su cámara y modelos de visión,
descubre peligros que el satélite no ve, replanifica y entrega a los
astronautas un **mapa por capas mejorado**, con cada decisión explicada.

Un panel de calibración permite cambiar en vivo la prioridad entre
**seguridad, ciencia, velocidad y energía**; el sistema cambia entre misiones
especializadas (segura / científica / rápida) según esos pesos.

## Para quién

- **Planificadores de misión en la Tierra** que preparan recorridos antes y
  durante la misión.
- **Astronautas en superficie** que necesitan un mapa confiable, con rutas,
  riesgos y objetivos, antes de salir del hábitat.

**Protagonista del pitch: el planificador de misión.** El panel de
calibración (005) se diseña para él; la vista final de la misión y el
reporte (009) se diseñan para que el astronauta los lea en superficie.

## Qué problema resuelve

1. **El mapa orbital no ve todos los peligros.** Arena blanda bajo costra
   (caso Spirit, 2009–2011), rocas afiladas o megarizaduras pequeñas no
   siempre se distinguen desde órbita.
2. **Los datos están dispersos** en decenas de misiones, instrumentos,
   formatos y convenciones de coordenadas.
3. **La planeación de rutas es lenta y manual**, y los primeros humanos
   estarán limitados a ~100 km del sitio de aterrizaje y a ~10 km de
   "walkback" (distancia para volver a pie si falla el vehículo).

## Qué lo hace distinto

- **El robot mejora el mapa de NASA antes de que llegue el humano**: el
  satélite da la planeación estratégica y el rover aporta la verdad en suelo.
- **Uso justificado del algoritmo genético**: no compite con A\* en ir de A a
  B; resuelve el problema combinatorio de *qué visitar y en qué orden* bajo
  restricciones de energía, walkback y zonas prohibidas (problema tipo
  orienteering), produciendo un frente de Pareto.
- **Switch de modelos explicable**: los sliders eligen un punto del frente de
  Pareto, y cada ruta dice por qué fue elegida ("evita una pendiente de 19°",
  "pasa por dos afloramientos").
- **Validación contra la realidad**: comparamos nuestras rutas en el cráter
  Jezero contra la ruta real de Perseverance.

## Fuera de alcance (por ahora)

- Hardware físico de rover y control de motores reales.
- Locomoción con patas o física de articulaciones (el rover se modela como
  navegación sobre terreno).
- Cobertura de todo Marte: una sola región de demostración (cráter Jezero).
- Predicción meteorológica operativa (los datos de InSight son históricos y
  de otra región; solo contexto).
- Cuentas de usuario, multiusuario o persistencia en base de datos.
