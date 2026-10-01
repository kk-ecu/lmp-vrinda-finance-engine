import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev server proxies /api to the FastAPI backend so the browser stays same-origin.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    // 5173 is Vite's default; avoids colliding with Podman's gvproxy on 3000.
    port: Number(process.env.VITE_PORT) || 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
