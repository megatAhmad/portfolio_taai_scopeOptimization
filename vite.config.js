/**
 * Vite Configuration
 * 
 * Configuration for Vite build tool with PostCSS support
 */

import { defineConfig } from 'vite';

export default defineConfig({
  root: '.',
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: {
        main: './docs/diagrams/index.html',
      },
    },
  },
  css: {
    postcss: './postcss.config.js',
  },
  server: {
    port: 3000,
    open: true,
  },
});
