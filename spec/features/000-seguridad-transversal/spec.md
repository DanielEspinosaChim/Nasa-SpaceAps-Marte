# Checklist de seguridad transversal

Referencia fija que se usa para auditar **cualquier** módulo del proyecto
antes de mergear. No es específico de una feature — aplica a todas.

**Contexto del proyecto:** demo pública de hackathon, sin cuentas de usuario
ni datos personales. La API es mayormente de lectura y tiene endpoints de
cómputo (rutas, misiones, simulación) que consumen CPU. Por eso el riesgo
principal no es el robo de datos sino **el abuso de cómputo, el path
traversal al servir archivos y los inputs malformados**.

## Los 11 puntos

1. **Validación de inputs**: todo input se valida en tipo, formato, longitud
   y rango antes de usarse, con modelos Pydantic: latitud en [−90, 90],
   longitud en [−180, 180], pesos en [0, 1], tamaño máximo de población y
   generaciones del genético, número máximo de waypoints. Las coordenadas
   fuera de la región cargada se rechazan con 422.
2. **Control de acceso**: no hay autenticación en el MVP porque es una demo
   pública de solo lectura sin datos sensibles. Ningún endpoint escribe o
   borra datos persistentes desde la web. Si se agrega un endpoint que
   modifique datos (por ejemplo, reemplazar datasets), ese endpoint debe
   protegerse con un token de administrador leído de una variable de
   entorno.
3. **Aislamiento multi-tenant**: **No aplica**. El proyecto no maneja
   múltiples clientes ni tenants; todas las sesiones ven los mismos datos
   públicos de NASA.
4. **Manejo de secrets**: ninguna credencial, token o llave (NASA API key,
   Context7 API key, etc.) está hardcodeada ni se sube al repositorio.
   `.env*` está en `.gitignore`, y existe un `.env.example` sin valores
   reales.
5. **Protección contra inyecciones**: no hay base de datos SQL. Nunca se
   construyen comandos de sistema ni rutas de archivo concatenando inputs.
   Los identificadores `region_id` y `layer_id` se validan contra una lista
   blanca cargada del disco, y nunca se usan directamente como ruta (protege
   contra path traversal `../`).
6. **Protección XSS/CSRF**: el frontend nunca inserta con `innerHTML` texto
   que venga de la API o de los datos, incluidas las explicaciones de ruta y
   los metadatos de capa; usa `textContent`. CORS restringido al origen del
   frontend configurado. No hay cookies de sesión, así que CSRF no aplica
   mientras no haya autenticación.
7. **Rate limiting**: los endpoints de cómputo (`/route`, `/mission`,
   `/simulate`) tienen límite por IP y un timeout máximo de cómputo por
   solicitud, para evitar la denegación de servicio por cómputo caro.
8. **Logging seguro**: no se registran API keys ni variables de entorno. Los
   logs de solicitudes guardan parámetros de cómputo, no cabeceras de
   autenticación.
9. **Manejo de errores**: los errores al cliente devuelven un mensaje y un
   código estables, sin stack traces, rutas internas del disco ni versiones
   de librerías. El detalle queda solo en el log del servidor.
10. **Dependencias**: sin vulnerabilidades conocidas (CVEs) sin mitigar o
    justificar. Revisar con `pip-audit` y `npm audit` antes de cada entrega.
11. **Subida de archivos**: **No aplica en el MVP**. Los datasets se cargan
    offline desde `data/raw/`. Si se agrega carga de datasets desde la web,
    validar el tipo real (cabecera GeoTIFF), un tamaño máximo y guardar fuera
    de rutas servidas.

## Formato de auditoría

Al auditar un módulo contra este checklist, reportar en el siguiente
formato:

```
Módulo: [nombre]
Fecha: [fecha]

1. Validación de inputs — [OK / P0 / P1 / P2 / No aplica] — [detalle si hay hallazgo]
2. Control de acceso — [...]
...
11. Subida de archivos — [...]

Resultado final: APROBADO / APROBADO CON OBSERVACIONES / RECHAZADO
```

- **P0**: crítico, bloquea el merge.
- **P1**: importante, debe resolverse pronto pero no bloquea si hay plan.
- **P2**: menor, mejora recomendada.
