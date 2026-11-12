import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// BASE_PATH is set by the GitHub Pages workflow ("/<repo>/"); "./" works for any static host.
export default defineConfig({
  base: process.env.BASE_PATH ?? './',
  plugins: [svelte()],
  worker: { format: 'es' },
  test: { include: ['src/**/*.test.ts'] },
});
