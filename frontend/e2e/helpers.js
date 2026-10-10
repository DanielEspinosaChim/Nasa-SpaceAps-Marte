// Ayudas E2E: abrir la app, encontrar celdas seguras vía API y hacer clic sobre coordenadas del mapa.

export async function openApp(page) {
  await page.goto('/?e2e=1');
  await page.waitForSelector('body[data-ready="true"]', { timeout: 30_000 });
  await page.waitForFunction(() => window.__app.map.loaded());
}

/** Puntos con transitabilidad 0 en una rejilla dentro del bbox (o de `around`). */
export async function freePoints(request, { around = null, spread = 0.9, n = 14 } = {}) {
  const regions = await (await request.get('/api/regions')).json();
  const [w, s, e, nn] = regions[0].bbox;
  const box = around
    ? [around.lon - 0.1, around.lat - 0.1, around.lon + 0.1, around.lat + 0.1]
    : [w + (e - w) * (1 - spread) / 2, s + (nn - s) * (1 - spread) / 2, e - (e - w) * (1 - spread) / 2, nn - (nn - s) * (1 - spread) / 2];
  const pts = [];
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const lon = box[0] + ((box[2] - box[0]) * i) / (n - 1);
      const lat = box[1] + ((box[3] - box[1]) * j) / (n - 1);
      const r = await request.get(`/api/regions/jezero/cell?lat=${lat}&lon=${lon}`);
      if (r.ok() && (await r.json()).traversability === 0) pts.push({ lat, lon });
    }
  }
  return pts;
}

/** Primer par de puntos (lejanos entre sí) que la API conecta con una ruta. */
export async function connectedPair(request, pts) {
  const far = [...pts].sort((a, b) => a.lon - b.lon);
  for (const a of far.slice(0, 6)) {
    for (const b of far.slice(-6)) {
      const r = await request.post('/api/regions/jezero/route', { data: { start: a, goal: b, preset: 'safe' } });
      if (r.ok() && (await r.json()).status === 'ok') return [a, b];
    }
  }
  throw new Error('no se encontró un par de puntos conectados');
}

/** Clic sobre la coordenada (lat, lon) del mapa. */
export async function clickLngLat(page, { lat, lon }) {
  const pos = await page.evaluate(({ lat, lon }) => {
    const p = window.__app.map.project([lon, lat]);
    return { x: p.x, y: p.y };
  }, { lat, lon });
  await page.locator('#map canvas.maplibregl-canvas').click({ position: pos });
}

export const numberOf = (text) => Number(text.replace(/[^\d.,-]/g, '').replace(',', '.'));

/** "6.4 km" / "850 m" → metros. */
export function metersOf(text) {
  return /km/.test(text) ? numberOf(text) * 1000 : numberOf(text);
}

export async function metricValue(page, testId, key) {
  const box = page.locator(`[data-testid="${testId}"] .metric`).filter({ hasText: key }).first();
  return (await box.locator('.v').textContent()).trim();
}
