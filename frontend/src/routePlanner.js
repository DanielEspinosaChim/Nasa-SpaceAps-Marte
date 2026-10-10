import { api } from './api.js';
import { clear, el } from './dom.js';
import { animateLine, clearGeoJSON, pinMarker } from './map.js';
import { renderRouteReport } from './routeReport.js';

const fmtPt = (p) => `${p.lat.toFixed(4)}° N, ${p.lon.toFixed(4)}° E`;

/**
 * Selección de inicio y destino (marcadores arrastrables), preset y cálculo de la ruta A*.
 * `ui.pick(hint, cb)` activa el modo "elegir punto en el mapa".
 */
export function createRoutePlanner({ container, map, regionId, presets, ui, toast }) {
  const state = { start: null, goal: null, markers: {}, hasRoute: false };

  const startBtn = el('button', { text: 'Elegir inicio', attrs: { id: 'pick-start', type: 'button' } });
  const goalBtn = el('button', { text: 'Elegir destino', attrs: { id: 'pick-goal', type: 'button' } });
  const startTxt = el('p', { class: 'coords', text: 'Inicio: sin elegir', attrs: { id: 'start-coords' } });
  const goalTxt = el('p', { class: 'coords', text: 'Destino: sin elegir', attrs: { id: 'goal-coords' } });
  const select = el('select', { attrs: { id: 'preset-select', 'aria-label': 'Preset de ruta' } });
  for (const p of presets) select.append(el('option', { text: p.label, attrs: { value: p.preset } }));
  select.value = presets.some((p) => p.preset === 'safe') ? 'safe' : presets[0].preset;
  const computeBtn = el('button', { class: 'primary', text: 'Calcular ruta', attrs: { id: 'compute-route', type: 'button' } });
  computeBtn.disabled = true;
  const result = el('div', { attrs: { id: 'route-result', 'aria-live': 'polite' } });

  function refresh() {
    startTxt.textContent = state.start ? `Inicio: ${fmtPt(state.start)}` : 'Inicio: sin elegir';
    goalTxt.textContent = state.goal ? `Destino: ${fmtPt(state.goal)}` : 'Destino: sin elegir';
    computeBtn.disabled = !(state.start && state.goal);
  }

  function place(kind, lngLat) {
    const pt = { lat: lngLat.lat, lon: lngLat.lng };
    state[kind] = pt;
    const marker = state.markers[kind];
    if (marker) marker.setLngLat([pt.lon, pt.lat]);
    else {
      state.markers[kind] = pinMarker(map, kind, kind === 'start' ? 'A' : 'B', [pt.lon, pt.lat], (ll) => {
        state[kind] = { lat: ll.lat, lon: ll.lng };
        refresh();
        if (state.hasRoute) compute();
      });
    }
    refresh();
  }

  function pick(kind) {
    ui.pick(kind === 'start' ? 'Haz clic en el mapa para elegir el inicio' : 'Haz clic en el mapa para elegir el destino', (ll) =>
      place(kind, ll),
    );
  }

  async function compute() {
    computeBtn.disabled = true;
    computeBtn.textContent = 'Calculando…';
    const res = await api.route(regionId, { start: state.start, goal: state.goal, preset: select.value });
    computeBtn.textContent = 'Calcular ruta';
    refresh();
    clear(result);
    if (!res.ok) {
      state.hasRoute = false;
      clearGeoJSON(map, 'route');
      result.append(el('p', { class: 'error', text: res.error.error }));
      toast(res.error.error);
      return;
    }
    const route = res.data;
    renderRouteReport(result, route);
    if (route.status === 'ok') {
      state.hasRoute = true;
      animateLine(map, 'route', route.geometry.coordinates);
    } else {
      state.hasRoute = false;
      clearGeoJSON(map, 'route');
    }
  }

  startBtn.addEventListener('click', () => pick('start'));
  goalBtn.addEventListener('click', () => pick('goal'));
  computeBtn.addEventListener('click', compute);

  container.append(
    el('div', { class: 'row' }, startBtn, goalBtn),
    startTxt,
    goalTxt,
    el('div', { class: 'row' }, el('label', { text: 'Preset', attrs: { for: 'preset-select' } }), select, computeBtn),
    result,
  );
  return { state, compute, place };
}
