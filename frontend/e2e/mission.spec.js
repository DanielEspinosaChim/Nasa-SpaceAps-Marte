import { expect, test } from '@playwright/test';
import { numberOf, metricValue, openApp } from './helpers.js';

test('planificar misión: paradas numeradas, misiones con nombre y descartes', async ({ page }) => {
  test.setTimeout(180_000);
  await openApp(page);

  // Hábitat = sitio de aterrizaje real de Perseverance (datos de NASA).
  await page.locator('#use-landing').click();
  await expect(page.locator('#habitat-coords')).toContainText('18.4446');
  await page.locator('#plan-mission').click();

  await expect(page.getByTestId('mission-metrics')).toBeVisible({ timeout: 60_000 });
  for (const label of ['Segura', 'Rápida', 'Científica', 'Balanceada']) {
    await expect(page.locator('#named-missions').getByRole('button', { name: label })).toBeVisible();
  }
  // Círculo de walkback y línea de misión dibujados.
  const hasWalkback = await page.evaluate(() => !!window.__app.map.getSource('walkback')._data.geometry);
  expect(hasWalkback).toBe(true);
  const legs = await page.evaluate(() => window.__app.map.getSource('mission-legs')._data.features.length);
  expect(legs).toBeGreaterThanOrEqual(2);
  // Marcadores numerados por orden de visita.
  const stops = await page.locator('.marker-stop').allTextContents();
  expect(stops.length).toBeGreaterThanOrEqual(1);
  expect(stops).toEqual(stops.map((_, i) => String(i + 1)));
  // Descartes con su razón (hay POI fuera del walkback de 10 km).
  await expect(page.getByTestId('mission-discarded')).toContainText(/walkback|zona prohibida|bloqueado|camino/);
  await expect(page.getByTestId('mission-explanations').locator('li').first()).toBeVisible();

  const sciBefore = numberOf(await metricValue(page, 'mission-metrics', 'Ciencia total'));
  await page.locator('#named-missions button[data-name="science"]').click();
  await expect(page.locator('#named-missions button[data-name="science"]')).toHaveClass(/active/);
  const sciAfter = numberOf(await metricValue(page, 'mission-metrics', 'Ciencia total'));
  expect(sciAfter).toBeGreaterThanOrEqual(sciBefore);
});

test('un hábitat en terreno bloqueado muestra un error claro', async ({ page }) => {
  await openApp(page);
  await page.route('**/api/regions/jezero/missions', (route) =>
    route.fulfill({ status: 422, json: { error: 'el hábitat cae en terreno bloqueado o en una zona prohibida', code: 'habitat_blocked' } }),
  );
  await page.locator('#use-landing').click();
  await page.locator('#plan-mission').click();
  await expect(page.locator('#mission-result .error')).toContainText('hábitat');
});
