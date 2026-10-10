import { el, fmtNum } from './dom.js';
import { maplibregl } from './map.js';

export const TRAV_LABEL = { 0: 'Segura (< 10°)', 1: 'Riesgo (10°–15°)', 2: 'Bloqueada (> 15°)' };

/** Filas [etiqueta, valor con unidades] de una celda; los valores nulos se muestran como "sin dato". */
export function formatCell(cell) {
  const val = (v, unit, d = 1) => (v == null ? 'sin dato' : `${fmtNum(v, d)} ${unit}`);
  return [
    ['Elevación', val(cell.elevation_m, 'm', 0)],
    ['Pendiente', val(cell.slope_deg, '°')],
    ['Rugosidad', val(cell.roughness_m, 'm', 2)],
    ['Transitabilidad', cell.traversability == null ? 'sin dato' : TRAV_LABEL[cell.traversability]],
    ['Coordenadas', `${fmtNum(cell.lat, 4)}° N, ${fmtNum(cell.lon, 4)}° E`],
  ];
}

export function cellContent(cell) {
  const dl = el('dl', { class: 'popup-grid' });
  for (const [k, v] of formatCell(cell)) dl.append(el('dt', { text: k }), el('dd', { text: v }));
  return dl;
}

export function showCellPopup(map, lngLat, cell) {
  return new maplibregl.Popup({ closeButton: true, maxWidth: '280px' })
    .setLngLat(lngLat)
    .setDOMContent(cellContent(cell))
    .addTo(map);
}
