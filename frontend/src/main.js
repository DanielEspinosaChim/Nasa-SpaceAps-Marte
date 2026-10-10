import './styles/index.css';
import { api } from './api.js';
import { showCellPopup } from './cellPopup.js';
import { createLayersPanel } from './layersPanel.js';
import { addLayerImages, addOverlays, createMap, setGeoJSON, setLayerOpacity, setLayerVisible } from './map.js';
import { createMissionPlanner } from './missionPlanner.js';
import { createRoutePlanner } from './routePlanner.js';

const $ = (id) => document.getElementById(id);

function toast(message) {
  const t = $('toast');
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.hidden = true), 6000);
}

async function main() {
  const regionsRes = await api.regions();
  if (!regionsRes.ok || regionsRes.data.length === 0) {
    $('region-name').textContent = regionsRes.ok
      ? 'No hay regiones procesadas. Ejecuta: python -m marsmap.terrain.build --region jezero --synthetic'
      : regionsRes.error.error;
    return;
  }
  const region = regionsRes.data[0];
  $('region-name').textContent = region.name;
  const [layersRes, poisRes, presetsRes] = await Promise.all([
    api.layers(region.region_id),
    api.pois(region.region_id),
    api.presets(region.region_id),
  ]);
  if (!layersRes.ok) return toast(layersRes.error.error);

  const map = createMap($('map'), region.bbox);
  const hint = $('mode-hint');
  const ui = {
    onPick: null,
    pick(text, cb) {
      ui.onPick = cb;
      hint.textContent = text;
      hint.hidden = false;
      map.getCanvas().style.cursor = 'crosshair';
    },
    cancel() {
      ui.onPick = null;
      hint.hidden = true;
      map.getCanvas().style.cursor = '';
    },
  };
  document.addEventListener('keydown', (e) => e.key === 'Escape' && ui.cancel());

  const sourceInfo = layersRes.data.find((l) => l.layer_id === 'elevation') || layersRes.data[0];
  $('region-name').textContent = `${region.name} · fuente: ${sourceInfo.source_dataset} (${sourceInfo.resolution_m} m/píxel)`;

  map.on('load', () => {
    addLayerImages(map, layersRes.data);
    addOverlays(map);
    if (poisRes.ok) setGeoJSON(map, 'pois', poisRes.data);

    createLayersPanel($('layers-panel'), layersRes.data, {
      onToggle: (id, visible) => setLayerVisible(map, id, visible),
      onOpacity: (id, opacity) => setLayerOpacity(map, id, opacity),
    });
    const route = createRoutePlanner({
      container: $('route-panel'),
      map,
      regionId: region.region_id,
      presets: presetsRes.ok ? presetsRes.data : [{ preset: 'balanced', label: 'Balanceada' }],
      ui,
      toast,
    });
    const mission = createMissionPlanner({
      container: $('mission-panel'),
      map,
      regionId: region.region_id,
      pois: poisRes.ok ? poisRes.data : { features: [] },
      ui,
      toast,
    });

    map.on('click', async (e) => {
      if (ui.onPick) {
        const cb = ui.onPick;
        ui.cancel();
        cb(e.lngLat);
        return;
      }
      const res = await api.cell(region.region_id, e.lngLat.lat, e.lngLat.lng);
      if (res.ok) showCellPopup(map, e.lngLat, res.data);
      else toast(res.error.error);
    });
    map.on('mouseenter', 'pois-circle', () => !ui.onPick && (map.getCanvas().style.cursor = 'pointer'));
    map.on('mouseleave', 'pois-circle', () => !ui.onPick && (map.getCanvas().style.cursor = ''));

    // Gancho de pruebas E2E: solo con ?e2e=1.
    if (new URLSearchParams(location.search).has('e2e')) window.__app = { map, ui, route, mission, region };
    document.body.dataset.ready = 'true';
  });
}

main();
