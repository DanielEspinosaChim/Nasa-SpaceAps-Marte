import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

// Orden de apilado (de abajo hacia arriba) de las capas raster.
export const STACK_ORDER = ['hillshade', 'elevation', 'roughness', 'slope', 'traversability'];

export const DEFAULT_LAYER_STATE = {
  hillshade: { visible: true, opacity: 1 },
  elevation: { visible: false, opacity: 0.7 },
  roughness: { visible: false, opacity: 0.7 },
  slope: { visible: false, opacity: 0.7 },
  traversability: { visible: true, opacity: 0.55 },
};

const EMPTY_STYLE = {
  version: 8,
  sources: {},
  layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#1a0f0a' } }],
};

const EMPTY_FC = { type: 'FeatureCollection', features: [] };

export function createMap(container, bbox) {
  const [w, s, e, n] = bbox;
  const map = new maplibregl.Map({
    container,
    style: EMPTY_STYLE,
    bounds: [[w, s], [e, n]],
    fitBoundsOptions: { padding: 30 },
    maxBounds: [[w - (e - w), s - (n - s)], [e + (e - w), n + (n - s)]],
    attributionControl: false,
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
  return map;
}

export function imageCoordinates(bbox) {
  const [w, s, e, n] = bbox;
  return [[w, n], [e, n], [e, s], [w, s]];
}

export function addLayerImages(map, layers) {
  const byId = Object.fromEntries(layers.map((l) => [l.layer_id, l]));
  for (const id of STACK_ORDER) {
    const layer = byId[id];
    if (!layer) continue;
    const st = DEFAULT_LAYER_STATE[id];
    map.addSource(`layer-${id}`, { type: 'image', url: layer.image_url, coordinates: imageCoordinates(layer.bbox) });
    map.addLayer({
      id: `layer-${id}`,
      type: 'raster',
      source: `layer-${id}`,
      layout: { visibility: st.visible ? 'visible' : 'none' },
      paint: { 'raster-opacity': st.opacity, 'raster-fade-duration': 0, 'raster-resampling': 'nearest' },
    });
  }
}

export function setLayerVisible(map, id, visible) {
  map.setLayoutProperty(`layer-${id}`, 'visibility', visible ? 'visible' : 'none');
}

export function setLayerOpacity(map, id, opacity) {
  map.setPaintProperty(`layer-${id}`, 'raster-opacity', opacity);
}

// Capas vectoriales de ruta, misión, POI y walkback (por encima de las rasters).
export function addOverlays(map) {
  for (const id of ['route', 'walkback', 'mission-legs', 'pois']) {
    map.addSource(id, { type: 'geojson', data: EMPTY_FC });
  }
  map.addLayer({
    id: 'walkback-line',
    type: 'line',
    source: 'walkback',
    paint: { 'line-color': '#7aa7ff', 'line-width': 2, 'line-dasharray': [3, 2] },
  });
  map.addLayer({
    id: 'route-casing',
    type: 'line',
    source: 'route',
    paint: { 'line-color': '#000', 'line-width': 7, 'line-opacity': 0.6 },
  });
  map.addLayer({
    id: 'route-line',
    type: 'line',
    source: 'route',
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: { 'line-color': '#ffd166', 'line-width': 4 },
  });
  map.addLayer({
    id: 'mission-casing',
    type: 'line',
    source: 'mission-legs',
    paint: { 'line-color': '#000', 'line-width': 7, 'line-opacity': 0.6 },
  });
  map.addLayer({
    id: 'mission-line',
    type: 'line',
    source: 'mission-legs',
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: {
      'line-color': ['step', ['get', 'risk'], '#3fa34d', 0.01, '#f2c14e', 0.25, '#d1495b'],
      'line-width': 4,
    },
  });
  map.addLayer({
    id: 'pois-circle',
    type: 'circle',
    source: 'pois',
    paint: {
      'circle-radius': 5,
      'circle-color': '#f2b66d',
      'circle-stroke-color': '#120a07',
      'circle-stroke-width': 1.5,
    },
  });
}

export function setGeoJSON(map, sourceId, data) {
  const src = map.getSource(sourceId);
  if (src) src.setData(data);
}

export function clearGeoJSON(map, sourceId) {
  setGeoJSON(map, sourceId, EMPTY_FC);
}

// Dibuja la línea progresivamente (animación de trazo).
export function animateLine(map, sourceId, coords, ms = 700) {
  if (!coords || coords.length < 2) return;
  const t0 = performance.now();
  const step = (now) => {
    const f = Math.min(1, (now - t0) / ms);
    const n = Math.max(2, Math.ceil(coords.length * f));
    setGeoJSON(map, sourceId, {
      type: 'Feature',
      properties: {},
      geometry: { type: 'LineString', coordinates: coords.slice(0, n) },
    });
    if (f < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// Polígono circular (lon/lat) de radio en metros alrededor de un punto: aproximación local.
export function circlePolygon(lat, lon, radiusM, n = 96) {
  const mPerDeg = (Math.PI * 3396190) / 180;
  const kx = mPerDeg * Math.cos((lat * Math.PI) / 180);
  const ring = [];
  for (let i = 0; i <= n; i++) {
    const a = (2 * Math.PI * i) / n;
    ring.push([lon + (radiusM * Math.cos(a)) / kx, lat + (radiusM * Math.sin(a)) / mPerDeg]);
  }
  return { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [ring] } };
}

const PIN_LABELS = { start: 'Inicio', goal: 'Destino', habitat: 'Hábitat' };

export function pinMarker(map, kind, text, lngLat, onDragEnd) {
  const node = document.createElement('div');
  node.className = `marker-pin ${kind}`;
  node.textContent = text;
  node.setAttribute('role', 'img');
  node.setAttribute('aria-label', PIN_LABELS[kind] || kind);
  const marker = new maplibregl.Marker({ element: node, draggable: true }).setLngLat(lngLat).addTo(map);
  if (onDragEnd) marker.on('dragend', () => onDragEnd(marker.getLngLat()));
  return marker;
}

export function stopMarker(map, number, lngLat, title) {
  const node = document.createElement('div');
  node.className = 'marker-stop';
  node.textContent = String(number);
  node.title = title;
  return new maplibregl.Marker({ element: node }).setLngLat(lngLat).addTo(map);
}

export { maplibregl };
