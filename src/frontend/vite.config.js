import { defineConfig } from 'vite';

export default defineConfig({
  optimizeDeps: {
    // MapLibre uses web workers internally; Vite's dependency pre-bundling
    // can break the worker initialisation, so we let the browser handle
    // the raw ESM directly.
    exclude: ['maplibre-gl']
  }
});
