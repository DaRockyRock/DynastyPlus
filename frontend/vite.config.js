/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The Flask backend serves the production build from `dist/`. During dev, run
// `npm run dev` (Vite on 5173) which proxies /api calls to Flask on 5050.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin';
import { playwright } from '@vitest/browser-playwright';
const dirname = typeof __dirname !== 'undefined' ? __dirname : path.dirname(fileURLToPath(import.meta.url));

// More info at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // Two app shells share one component library: index.html is the Dynasty+
    // companion, simulator.html is the Simulator (CFB 27 stand-in). Each is
    // served in production by its own Flask backend from this same dist/.
    rollupOptions: {
      input: {
        main: path.resolve(dirname, 'index.html'),
        simulator: path.resolve(dirname, 'simulator.html'),
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Dynasty+ companion backend.
      '/api': 'http://127.0.0.1:5050',
      // Simulator backend. The simulator entry sets window.__API_BASE__ to
      // '/sim-api' in dev; strip the prefix so it reaches the Simulator's /api.
      '/sim-api': {
        target: 'http://127.0.0.1:5070',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/sim-api/, ''),
      },
    },
  },
  test: {
    projects: [{
      extends: true,
      plugins: [
      // The plugin will run tests for the stories defined in your Storybook config
      // See options at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon#storybooktest
      storybookTest({
        configDir: path.join(dirname, '.storybook')
      })],
      test: {
        name: 'storybook',
        browser: {
          enabled: true,
          headless: true,
          provider: playwright({}),
          instances: [{
            browser: 'chromium'
          }]
        }
      }
    }]
  }
});