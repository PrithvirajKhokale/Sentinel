import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxy target: the local backend by default, or a deployed API such as
// https://sentinel-api-waat.onrender.com (avoids CORS; the token stays in the UI).
const apiTarget = process.env.SENTINEL_API_PROXY_TARGET || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173,
    proxy: { "/api": { target: apiTarget, changeOrigin: true } } },
  build: { outDir: "dist" },
});
