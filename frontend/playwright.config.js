import { defineConfig } from '@playwright/test';

// E2E contra un backend real que sirve frontend/dist y los datos sintéticos de data/processed.
// Antes: `python -m marsmap.terrain.build --region jezero --synthetic` y `npm run build`.
const PY = process.env.PYTHON || 'python';

export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  retries: 0,
  workers: 1, // en serie: la prueba de tiempo de carga no es válida si compite por CPU con otras
  use: {
    baseURL: 'http://127.0.0.1:8000',
    launchOptions: { args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] },
  },
  webServer: {
    command: `${PY} -m uvicorn marsmap.api.main:app --port 8000`,
    cwd: '..',
    url: 'http://127.0.0.1:8000/api/health',
    reuseExistingServer: true,
    timeout: 60_000,
    env: {
      FRONTEND_DIST: 'frontend/dist',
      DATA_DIR: 'data/processed',
      RATE_LIMIT_PER_MINUTE: '1000',
      MISSION_RATE_LIMIT_PER_MINUTE: '100',
    },
  },
});
