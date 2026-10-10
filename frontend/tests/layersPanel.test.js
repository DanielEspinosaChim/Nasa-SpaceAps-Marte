import { describe, expect, it, vi } from 'vitest';

// MapLibre necesita WebGL y no carga en jsdom: la lógica probada aquí no depende del mapa real.
vi.mock('maplibre-gl', () => {
  class Stub {}
  return { default: { Map: Stub, Popup: Stub, Marker: Stub, NavigationControl: Stub } };
});

import { cellContent, formatCell } from '../src/cellPopup.js';
import { circlePolygon, imageCoordinates } from '../src/map.js';
import { createLayersPanel, sortLayers } from '../src/layersPanel.js';
import { legFeatures } from '../src/missionLayer.js';
import { renderMissionReport } from '../src/missionReport.js';
import { profileBounds } from '../src/profileChart.js';
import { el } from '../src/dom.js';

const XSS = '<img src=x onerror="window.__pwned=1">';

const layer = (id, extra = {}) => ({
  layer_id: id,
  name: `Capa ${id}`,
  units: 'm',
  source_dataset: 'synthetic(seed=42)',
  instrument: 'Generador',
  resolution_m: 200,
  generated_at: '2026-10-09T00:00:00Z',
  limitations: 'Sin rocas individuales',
  legend: [{ value: 0, color: '#3fa34d', label: 'Segura' }],
  bbox: [77, 18, 78, 18.9],
  ...extra,
});

describe('panel de capas', () => {
  it('muestra las 5 capas con toggle, opacidad, leyenda y ficha', () => {
    const root = document.createElement('div');
    const ids = ['elevation', 'slope', 'roughness', 'hillshade', 'traversability'];
    createLayersPanel(root, ids.map((i) => layer(i)), { onToggle() {}, onOpacity() {} });
    expect(root.querySelectorAll('input[type=checkbox]')).toHaveLength(5);
    expect(root.querySelectorAll('input[type=range]')).toHaveLength(5);
    expect(root.querySelectorAll('ul.legend')).toHaveLength(5);
    expect(root.querySelectorAll('details.source')).toHaveLength(5);
    expect(root.textContent).toContain('synthetic(seed=42)');
    expect(root.textContent).toContain('Sin rocas individuales');
  });

  it('el toggle y el slider llaman a los handlers (opacidad 0–100 → 0..1)', () => {
    const root = document.createElement('div');
    const onToggle = vi.fn();
    const onOpacity = vi.fn();
    createLayersPanel(root, [layer('slope')], { onToggle, onOpacity });
    const chk = root.querySelector('input[type=checkbox]');
    chk.checked = true;
    chk.dispatchEvent(new Event('change'));
    expect(onToggle).toHaveBeenCalledWith('slope', true);
    const range = root.querySelector('input[type=range]');
    range.value = '35';
    range.dispatchEvent(new Event('input'));
    expect(onOpacity).toHaveBeenCalledWith('slope', 0.35);
  });

  it('inserta texto de la API con textContent (sin ejecutar HTML)', () => {
    const root = document.createElement('div');
    createLayersPanel(root, [layer('slope', { name: XSS, limitations: XSS, source_dataset: XSS })], {
      onToggle() {},
      onOpacity() {},
    });
    expect(root.querySelector('img')).toBeNull();
    expect(root.textContent).toContain('<img src=x');
  });

  it('ignora colores de leyenda que no sean #rrggbb', () => {
    const root = document.createElement('div');
    createLayersPanel(
      root,
      [layer('slope', { legend: [{ value: 0, color: 'url(javascript:alert(1))', label: 'x' }] })],
      { onToggle() {}, onOpacity() {} },
    );
    expect(root.querySelector('.swatch').style.background).toBe('transparent');
  });

  it('ordena la transitabilidad primero', () => {
    const sorted = sortLayers([layer('hillshade'), layer('traversability'), layer('elevation')]);
    expect(sorted.map((l) => l.layer_id)).toEqual(['traversability', 'elevation', 'hillshade']);
  });
});

describe('popup de celda', () => {
  it('formatea valores con unidades y maneja nodata', () => {
    const rows = Object.fromEntries(
      formatCell({ lat: 18.4, lon: 77.5, elevation_m: -2500.4, slope_deg: 8.44, roughness_m: 1.234, traversability: 1 }),
    );
    expect(rows['Elevación']).toBe('-2500 m');
    expect(rows['Pendiente']).toBe('8.4 °');
    expect(rows['Transitabilidad']).toContain('Riesgo');
    const empty = Object.fromEntries(
      formatCell({ lat: 18.4, lon: 77.5, elevation_m: null, slope_deg: null, roughness_m: null, traversability: null }),
    );
    expect(empty['Pendiente']).toBe('sin dato');
  });

  it('no interpreta HTML en el contenido', () => {
    const node = cellContent({ lat: 1, lon: 2, elevation_m: 1, slope_deg: 1, roughness_m: 1, traversability: 0 });
    expect(node.querySelectorAll('dt')).toHaveLength(5);
  });
});

describe('geometría y misión', () => {
  it('las esquinas de imagen siguen el orden NO, NE, SE, SO', () => {
    expect(imageCoordinates([77, 18, 78, 18.9])).toEqual([[77, 18.9], [78, 18.9], [78, 18], [77, 18]]);
  });

  it('el círculo de walkback mide ~10 km de radio', () => {
    const c = circlePolygon(18.4, 77.5, 10000).geometry.coordinates[0];
    const mPerDeg = (Math.PI * 3396190) / 180;
    const [lon, lat] = c[0];
    const dx = (lon - 77.5) * mPerDeg * Math.cos((18.4 * Math.PI) / 180);
    const dy = (lat - 18.4) * mPerDeg;
    expect(Math.hypot(dx, dy)).toBeCloseTo(10000, -1);
    expect(c[0]).toEqual(c[c.length - 1]);
  });

  it('colorea cada tramo por la fracción de riesgo', () => {
    const mission = {
      legs: [
        { from: 'habitat', to: 'a', distance_m: 1000, risk_m: 0, coordinates: [[1, 1], [2, 2]] },
        { from: 'a', to: 'habitat', distance_m: 1000, risk_m: 500, coordinates: [[2, 2], [1, 1]] },
        { from: 'x', to: 'y', distance_m: 0, risk_m: 0, coordinates: [[1, 1]] },
      ],
    };
    const f = legFeatures(mission);
    expect(f).toHaveLength(2);
    expect(f.map((x) => x.properties.risk)).toEqual([0, 0.5]);
  });

  it('el reporte de misión usa textContent y lista paradas, explicaciones y descartes', () => {
    const root = document.createElement('div');
    const result = {
      named: { safe: 'm00', fast: 'm00', science: 'm01', balanced: 'm00' },
      discarded: [{ poi_id: 'z', reason_code: 'outside_walkback', reason: `Descarta ${XSS}` }],
      limitations: ['Modelo genérico'],
    };
    const mission = {
      mission_id: 'm00', sequence: ['a'], explanations: [XSS], science_total: 1.2, time_h: 10, energy_wh: 100,
      risk_score: 0, distance_m: 5000, max_slope_deg: 3,
    };
    renderMissionReport(root, result, mission, { a: { name: XSS } });
    expect(root.querySelector('img')).toBeNull();
    expect(root.querySelectorAll('[data-testid=mission-stops] li')).toHaveLength(1);
    expect(root.querySelectorAll('[data-testid=mission-discarded] li')).toHaveLength(1);
    expect(root.textContent).toContain('segura / rápida / balanceada');
    expect(window.__pwned).toBeUndefined();
  });
});

describe('perfil y dom', () => {
  it('calcula los límites del perfil aunque sea plano', () => {
    expect(profileBounds([{ d_m: 0, elev_m: 5 }, { d_m: 100, elev_m: 5 }])).toEqual({ lo: 5, hi: 6, total: 100 });
  });

  it('el helper el() no interpreta HTML', () => {
    const n = el('p', { text: XSS });
    expect(n.querySelector('img')).toBeNull();
    expect(n.textContent).toBe(XSS);
  });
});
