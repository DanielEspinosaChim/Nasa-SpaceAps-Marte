import { api } from './api.js';
import { clear, el } from './dom.js';
import { pinMarker } from './map.js';
import { createMissionLayer } from './missionLayer.js';
import { MISSION_LABEL, renderMissionReport } from './missionReport.js';

// Sitio de aterrizaje de Perseverance: primer waypoint (sol 13) de la capa M20_waypoints de NASA.
const LANDING = { lat: 18.44462715, lon: 77.45088572 };
const NAMED = ['safe', 'fast', 'science', 'balanced'];

function field(id, label, value, attrs) {
  const input = el('input', { attrs: { id, type: 'number', value, ...attrs } });
  return [el('label', { text: label, attrs: { for: id } }), input];
}

export function createMissionPlanner({ container, map, regionId, pois, ui, toast }) {
  const layer = createMissionLayer(map);
  const poisById = Object.fromEntries(
    pois.features.map((f) => [f.properties.poi_id, { ...f.properties, coordinates: f.geometry.coordinates }]),
  );
  const state = { habitat: null, marker: null, result: null, shown: null };

  const pickBtn = el('button', { text: 'Elegir hábitat', attrs: { id: 'pick-habitat', type: 'button' } });
  const landingBtn = el('button', { text: 'Usar sitio de aterrizaje', attrs: { id: 'use-landing', type: 'button' } });
  const habTxt = el('p', { class: 'coords', text: 'Hábitat: sin elegir', attrs: { id: 'habitat-coords' } });
  const [lE, iE] = field('energy-budget', 'Energía (Wh)', 12000, { min: 100, max: 50000, step: 100 });
  const [lT, iT] = field('max-time', 'Tiempo máx. (h)', 240, { min: 1, max: 720, step: 1 });
  const [lR, iR] = field('walkback-km', 'Walkback (km)', 10, { min: 1, max: 100, step: 1 });
  const planBtn = el('button', { class: 'primary', text: 'Planificar misión', attrs: { id: 'plan-mission', type: 'button' } });
  planBtn.disabled = true;
  const named = el('div', { class: 'row', attrs: { id: 'named-missions', role: 'group', 'aria-label': 'Misiones del frente de Pareto' } });
  const report = el('div', { attrs: { id: 'mission-result', 'aria-live': 'polite' } });

  function refresh() {
    habTxt.textContent = state.habitat
      ? `Hábitat: ${state.habitat.lat.toFixed(4)}° N, ${state.habitat.lon.toFixed(4)}° E`
      : 'Hábitat: sin elegir';
    planBtn.disabled = !state.habitat;
  }

  function setHabitat(lngLat) {
    state.habitat = { lat: lngLat.lat, lon: lngLat.lng };
    if (state.marker) state.marker.setLngLat([state.habitat.lon, state.habitat.lat]);
    else {
      state.marker = pinMarker(map, 'habitat', 'H', [state.habitat.lon, state.habitat.lat], (ll) => {
        state.habitat = { lat: ll.lat, lon: ll.lng };
        refresh();
      });
    }
    refresh();
  }

  function show(missionId) {
    const mission = state.result.front.find((m) => m.mission_id === missionId);
    state.shown = mission;
    layer.draw(mission, poisById);
    renderMissionReport(report, state.result, mission, poisById);
    for (const b of named.querySelectorAll('button')) b.classList.toggle('active', b.dataset.id === missionId);
  }

  function renderNamed() {
    clear(named);
    for (const key of NAMED) {
      const id = state.result.named[key];
      const btn = el('button', { text: MISSION_LABEL[key], attrs: { type: 'button', 'data-name': key, 'data-id': id } });
      btn.addEventListener('click', () => show(id));
      named.append(btn);
    }
  }

  async function plan() {
    planBtn.disabled = true;
    planBtn.textContent = 'Optimizando…';
    const radiusM = Number(iR.value) * 1000;
    const res = await api.missions(regionId, {
      habitat: state.habitat,
      energy_budget_wh: Number(iE.value),
      max_time_h: Number(iT.value),
      max_radius_m: radiusM,
    });
    planBtn.textContent = 'Planificar misión';
    refresh();
    clear(report);
    clear(named);
    if (!res.ok) {
      layer.clear();
      report.append(el('p', { class: 'error', text: res.error.error }));
      toast(res.error.error);
      return;
    }
    state.result = res.data;
    layer.drawWalkback(state.habitat, res.data.params_used.max_radius_m);
    renderNamed();
    show(res.data.named.balanced);
  }

  pickBtn.addEventListener('click', () =>
    ui.pick('Haz clic en el mapa para elegir el hábitat', (ll) => setHabitat(ll)),
  );
  landingBtn.addEventListener('click', () => setHabitat({ lat: LANDING.lat, lng: LANDING.lon }));
  planBtn.addEventListener('click', plan);

  container.append(
    el('div', { class: 'row' }, pickBtn, landingBtn),
    habTxt,
    el('div', { class: 'row' }, lE, iE),
    el('div', { class: 'row' }, lT, iT),
    el('div', { class: 'row' }, lR, iR),
    el('div', { class: 'row' }, planBtn),
    named,
    report,
  );
  return { state, plan, show, setHabitat };
}
