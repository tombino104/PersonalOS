import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

const backend = process.env.BACKEND_URL ?? 'http://127.0.0.1:47213';
const demo = process.env.DEMO === '1';

function appVersion() {
  try {
    return readFileSync(new URL('../app/__init__.py', import.meta.url), 'utf8').match(/__version__ = "([^"]+)"/)?.[1] ?? '';
  } catch {
    return '';
  }
}

const version = appVersion();

export default defineConfig({
  base: demo ? (process.env.DEMO_BASE ?? '/PersonalOS/') : '/',
  define: {
    __DEMO__: JSON.stringify(demo),
    __APP_VERSION__: JSON.stringify(version),
  },
  plugins: [svelte()],
  resolve: {
    alias: {
      $core: fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/api': backend,
      '/health': backend,
    },
  },
  test: {
    include: ['src/**/*.test.js'],
  },
});
