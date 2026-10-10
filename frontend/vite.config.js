import { defineConfig } from 'vite';

// En desarrollo, /api se redirige al backend (uvicorn en :8000). En producción FastAPI sirve dist/.
export default defineConfig({
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } },
  build: { outDir: 'dist', chunkSizeWarningLimit: 1200 },
  test: { environment: 'jsdom', include: ['tests/**/*.test.js'] },
});
