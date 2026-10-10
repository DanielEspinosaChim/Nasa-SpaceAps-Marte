import { clear, el, explanationList, fmtKm, fmtNum, metric } from './dom.js';
import { drawProfile } from './profileChart.js';

/** Tarjeta de métricas, perfil altimétrico y explicaciones de una ruta (todo con textContent). */
export function renderRouteReport(container, route) {
  clear(container);
  if (route.status !== 'ok') {
    container.append(el('p', { class: 'empty', text: route.reason || 'No existe una ruta posible.' }));
    return;
  }
  container.append(
    el(
      'div',
      { class: 'metrics', attrs: { 'data-testid': 'route-metrics' } },
      metric('Distancia', fmtKm(route.distance_m)),
      metric('Línea recta', fmtKm(route.straight_line_m)),
      metric('Tortuosidad', fmtNum(route.tortuosity, 2)),
      metric('Pend. máxima', `${fmtNum(route.max_slope_deg)}°`),
      metric('Pend. media', `${fmtNum(route.mean_slope_deg)}°`),
      metric('Desnivel', `+${fmtNum(route.elevation_gain_m, 0)} / −${fmtNum(route.elevation_loss_m, 0)} m`),
      metric('Terreno de riesgo', `${fmtNum(route.pct_risk_cells, 0)}%`),
      metric('Tiempo estimado', `${fmtNum(route.est_time_h)} h`),
    ),
  );
  const canvas = el('canvas', { class: 'profile', attrs: { 'aria-label': 'Perfil altimétrico', role: 'img' } });
  container.append(el('h3', { text: 'Perfil altimétrico' }), canvas);
  requestAnimationFrame(() => drawProfile(canvas, route.profile));
  container.append(
    el('h3', { text: '¿Por qué esta ruta?' }),
    el('div', { attrs: { 'data-testid': 'route-explanations' } }, explanationList(route.explanations)),
  );
}
