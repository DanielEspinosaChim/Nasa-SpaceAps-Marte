import { el } from './dom.js';

export const DEFAULTS = {
  hillshade: { visible: true, opacity: 1 },
  elevation: { visible: false, opacity: 0.7 },
  roughness: { visible: false, opacity: 0.7 },
  slope: { visible: false, opacity: 0.7 },
  traversability: { visible: true, opacity: 0.55 },
};

// Orden en el panel: primero lo que más se consulta.
const PANEL_ORDER = ['traversability', 'slope', 'elevation', 'roughness', 'hillshade'];

export function sortLayers(layers) {
  const rank = (l) => {
    const i = PANEL_ORDER.indexOf(l.layer_id);
    return i === -1 ? PANEL_ORDER.length : i;
  };
  return [...layers].sort((a, b) => rank(a) - rank(b));
}

function sourceCard(layer) {
  const rows = [
    ['Fuente', layer.source_dataset],
    ['Instrumento', layer.instrument],
    ['Resolución', `${layer.resolution_m} m/píxel`],
    ['Unidades', layer.units],
    ['Generada', layer.generated_at],
    ['Limitaciones', layer.limitations],
  ];
  const dl = el('dl');
  for (const [k, v] of rows) dl.append(el('dt', { text: k }), el('dd', { text: v }));
  return el('details', { class: 'source' }, el('summary', { text: 'Fuente y limitaciones' }), dl);
}

function legendList(layer) {
  return el(
    'ul',
    { class: 'legend', attrs: { 'aria-label': `Leyenda de ${layer.name}` } },
    layer.legend.map((item) => {
      const sw = el('span', { class: 'swatch' });
      sw.style.background = /^#[0-9a-fA-F]{6}$/.test(item.color) ? item.color : 'transparent';
      return el('li', {}, sw, el('span', { text: item.label }));
    }),
  );
}

/**
 * Panel de capas: activar/desactivar, opacidad (0–100 %), leyenda y ficha de fuente.
 * handlers.onToggle(layerId, visible) y handlers.onOpacity(layerId, opacity 0..1).
 */
export function createLayersPanel(container, layers, handlers, defaults = DEFAULTS) {
  container.replaceChildren();
  for (const layer of sortLayers(layers)) {
    const st = defaults[layer.layer_id] || { visible: false, opacity: 0.7 };
    const checkId = `chk-${layer.layer_id}`;
    const opId = `op-${layer.layer_id}`;
    const check = el('input', {
      attrs: { type: 'checkbox', id: checkId, 'data-layer': layer.layer_id },
      on: { change: (e) => handlers.onToggle(layer.layer_id, e.target.checked) },
    });
    check.checked = st.visible;
    const slider = el('input', {
      attrs: {
        type: 'range', min: 0, max: 100, step: 1, id: opId, 'data-layer': layer.layer_id,
        'aria-label': `Opacidad de ${layer.name}`,
      },
      on: { input: (e) => handlers.onOpacity(layer.layer_id, Number(e.target.value) / 100) },
    });
    slider.value = String(Math.round(st.opacity * 100));
    container.append(
      el(
        'div',
        { class: 'layer', attrs: { 'data-testid': `layer-${layer.layer_id}` } },
        el('div', { class: 'layer-head' }, check, el('label', { text: layer.name, attrs: { for: checkId } })),
        el('div', { class: 'opacity' }, el('span', { text: 'Opacidad' }), slider),
        legendList(layer),
        sourceCard(layer),
      ),
    );
  }
  return container;
}
