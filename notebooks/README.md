# Notebook de demostración

**`Mars_Scout_demo.html`** — ábrelo con doble clic en cualquier navegador. Ya trae todos los gráficos y
resultados incluidos; no necesita Python ni internet. Es lo más cómodo para mostrar o enviar por correo.

**`Mars_Scout_demo.ipynb`** — el mismo documento como notebook. Ya está ejecutado, así que también se ve
sin correr nada (VS Code, Cursor o Jupyter lo abren). Si quieres volver a ejecutarlo, elige el kernel
**«Mars Scout (.venv)»** y pulsa *Run All* (≈ 30 s).

## Qué muestra
1. Los datos reales (relieve de Marte y sitios y recorrido reales de Perseverance).
2. Lo que hizo NASA.
3. Cómo lo resolvimos: mapa de riesgo → rutas A* → algoritmo genético → misiones.
4. Comparación NASA vs nosotros, con sus límites.
5. Pruebas de que el algoritmo funciona.

## Regenerarlo
```
python scripts/build_notebook.py
```
Necesita los datos reales (`data/raw/jezero/…`, ver `data/README.md`) y las librerías del extra
`notebook` (`pip install -e ".[notebook]"`). Las funciones de los gráficos están en
`src/marsmap/notebook_tools.py`.

> Solo funciona dentro del proyecto: usa el paquete `marsmap` y los datos de `data/`.
> Para compartirlo fuera, usa el `.html`.
