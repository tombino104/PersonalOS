import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

const backend = process.env.BACKEND_URL ?? 'http://127.0.0.1:47213';

export default defineConfig({
  plugins: [svelte()],
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
