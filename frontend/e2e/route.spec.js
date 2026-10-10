import { expect, test } from '@playwright/test';
import { clickLngLat, connectedPair, freePoints, metersOf, metricValue, openApp } from './helpers.js';

test('elegir inicio y destino, calcular ruta segura y rápida', async ({ page, request }) => {
  test.setTimeout(180_000);
  const pts = await freePoints(request);
  const [a, b] = await connectedPair(request, pts);
  await openApp(page);

  await page.locator('#pick-start').click();
  await expect(page.locator('#mode-hint')).toBeVisible();
  await clickLngLat(page, a);
  await expect(page.locator('#start-coords')).toContainText('Inicio:');
  await page.locator('#pick-goal').click();
  await clickLngLat(page, b);
  await expect(page.locator('#goal-coords')).toContainText('Destino:');
  await expect(page.locator('#compute-route')).toBeEnabled();

  await page.locator('#preset-select').selectOption('safe');
  await page.locator('#compute-route').click();
  await expect(page.getByTestId('route-metrics')).toBeVisible();
  await expect(page.locator('canvas.profile')).toBeVisible();
  const explanations = page.getByTestId('route-explanations').locator('li');
  expect(await explanations.count()).toBeGreaterThanOrEqual(1);
  await page.waitForTimeout(900); // termina la animación de trazo
  const drawn = await page.evaluate(() => window.__app.map.getSource('route')._data.geometry.coordinates.length);
  expect(drawn).toBeGreaterThan(2);
  const safe = metersOf(await metricValue(page, 'route-metrics', 'Distancia'));

  await page.locator('#preset-select').selectOption('fast');
  await page.locator('#compute-route').click();
  await expect(page.getByTestId('route-metrics')).toBeVisible();
  await expect.poll(async () => metersOf(await metricValue(page, 'route-metrics', 'Distancia'))).toBeLessThanOrEqual(safe);
});

test('un inicio en terreno bloqueado muestra un error claro', async ({ page, request }) => {
  const free = (await freePoints(request, { n: 6 }))[0];
  await openApp(page);
  // Celda bloqueada: busca una vía API.
  let blocked = null;
  for (let i = 0; i < 40 && !blocked; i++) {
    const lon = 77.0 + 0.025 * i;
    for (let j = 0; j < 40 && !blocked; j++) {
      const lat = 18.0 + 0.0225 * j;
      const r = await request.get(`/api/regions/jezero/cell?lat=${lat}&lon=${lon}`);
      if (r.ok() && (await r.json()).traversability === 2) blocked = { lat, lon };
    }
  }
  expect(blocked).not.toBeNull();
  await page.locator('#pick-start').click();
  await clickLngLat(page, blocked);
  await page.locator('#pick-goal').click();
  await clickLngLat(page, free);
  await page.locator('#compute-route').click();
  await expect(page.locator('#route-result .error')).toContainText(/bloqueado|zona prohibida/);
});
