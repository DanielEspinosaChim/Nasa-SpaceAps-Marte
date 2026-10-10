import { expect, test } from '@playwright/test';
import { clickLngLat, freePoints, openApp } from './helpers.js';

const LAYERS = ['traversability', 'slope', 'elevation', 'roughness', 'hillshade'];

test('la app carga en menos de 3 s y muestra las 5 capas con su ficha', async ({ page }) => {
  const t0 = Date.now();
  await openApp(page);
  expect(Date.now() - t0).toBeLessThan(3000);
  await expect(page.locator('h1')).toHaveText('Mars Scout');
  for (const id of LAYERS) await expect(page.getByTestId(`layer-${id}`)).toBeVisible();
  const card = page.getByTestId('layer-slope').locator('details.source');
  await card.locator('summary').click();
  await expect(card).toContainText('Fuente');
  await expect(card).toContainText('Resolución');
  await expect(card).toContainText('Limitaciones');
});

test('activar capas y cambiar su opacidad se refleja en el mapa en < 100 ms', async ({ page }) => {
  await openApp(page);
  const vis = (id) => page.evaluate((i) => window.__app.map.getLayoutProperty(`layer-${i}`, 'visibility'), id);
  expect(await vis('elevation')).toBe('none');
  await page.locator('#chk-elevation').check();
  expect(await vis('elevation')).toBe('visible');
  await page.locator('#chk-elevation').uncheck();
  expect(await vis('elevation')).toBe('none');

  const ms = await page.evaluate(() => {
    const slider = document.getElementById('op-slope');
    const t0 = performance.now();
    slider.value = '40';
    slider.dispatchEvent(new Event('input', { bubbles: true }));
    const v = window.__app.map.getPaintProperty('layer-slope', 'raster-opacity');
    return { dt: performance.now() - t0, v };
  });
  expect(ms.v).toBeCloseTo(0.4, 2);
  expect(ms.dt).toBeLessThan(100);
});

test('clic en el mapa abre un popup con los valores de la celda y sus unidades', async ({ page, request }) => {
  await openApp(page);
  const [p] = await freePoints(request, { n: 6 });
  await clickLngLat(page, p);
  const popup = page.locator('.maplibregl-popup');
  await expect(popup).toBeVisible();
  for (const k of ['Elevación', 'Pendiente', 'Rugosidad', 'Transitabilidad']) await expect(popup).toContainText(k);
  await expect(popup).toContainText(/ m/);
  await expect(popup).toContainText('°');
});

test('el texto de la API nunca se inserta como HTML', async ({ page }) => {
  await page.route('**/api/regions/jezero/layers', async (route) => {
    const res = await route.fetch();
    const body = await res.json();
    body[0].name = '<img src=x onerror="window.__pwned=1">';
    body[0].limitations = '<script>window.__pwned=1</script>';
    await route.fulfill({ response: res, json: body });
  });
  await openApp(page);
  expect(await page.evaluate(() => window.__pwned)).toBeUndefined();
  await expect(page.locator('#layers-panel img')).toHaveCount(0);
  await expect(page.locator('#layers-panel')).toContainText('<img src=x');
});
