import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During the strangler migration the SPA is served under /app by FastAPI.
// In dev, proxy the live API so the SPA hits the real backend on :8080.
export default defineConfig({
  base: "/app/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8080",
      "/sessions": "http://localhost:8080",
      "/teams": "http://localhost:8080",
      "/archives": "http://localhost:8080",
    },
  },
  build: {
    outDir: "dist",
  },
});
