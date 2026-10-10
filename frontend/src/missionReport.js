import { clear, el, explanationList, fmtKm, fmtNum, metric } from './dom.js';

export const MISSION_LABEL = { safe: 'Segura', fast: 'Rápida', science: 'Científica', balanced: 'Balanceada' };

/** Métricas, secuencia, explicaciones y POI descartados de una misión (todo con textContent). */
export function renderMissionReport(container, result, mission, poisById) {
  clear(container);
  const names = Object.entries(result.named)
    .filter(([, id]) => id === mission.mission_id)
    .map(([k]) => MISSION_LABEL[k]);
  container.append(
    el('h3', { text: names.length ? `Misión ${names.join(' / ').toLowerCase()}` : `Misión ${mission.mission_id}` }),
    el(
      'div',
      { class: 'metrics', attrs: { 'data-testid': 'mission-metrics' } },
      metric('Ciencia total', fmtNum(mission.science_total, 2)),
      metric('Tiempo', `${fmtNum(mission.time_h)} h`),
      metric('Energía', `${fmtNum(mission.energy_wh, 0)} Wh`),
      metric('Riesgo', fmtNum(mission.risk_score, 0)),
      metric('Distancia', fmtKm(mission.distance_m)),
      metric('Pend. máxima', `${fmtNum(mission.max_slope_deg)}°`),
    ),
  );
  const stops = mission.sequence.map((id) => (poisById[id] ? poisById[id].name : id));
  container.append(
    el('h3', { text: 'Paradas' }),
    stops.length
      ? el('ol', { attrs: { 'data-testid': 'mission-stops' } }, stops.map((s) => el('li', { text: s })))
      : el('p', { class: 'empty', text: 'Ninguna: el rover permanece en el hábitat.' }),
    el('h3', { text: '¿Por qué esta misión?' }),
    el('div', { attrs: { 'data-testid': 'mission-explanations' } }, explanationList(mission.explanations)),
  );
  if (result.discarded.length) {
    container.append(
      el('h3', { text: 'Puntos descartados antes de optimizar' }),
      el(
        'ul',
        { class: 'explain', attrs: { 'data-testid': 'mission-discarded' } },
        result.discarded.map((d) => el('li', { text: d.reason })),
      ),
    );
  }
  container.append(
    el('details', { class: 'source' }, el('summary', { text: 'Limitaciones' }), explanationList(result.limitations)),
  );
}
