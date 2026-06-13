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
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        // Split heavy, rarely-changing vendor code so the browser caches it
        // across app deploys instead of re-downloading one giant bundle.
        manualChunks(id) {
          if (!id.includes("node_modules")) return;
          if (id.includes("mantine-react-table") || id.includes("@tanstack")) return "table";
          if (id.includes("@mantine") || id.includes("@tabler")) return "mantine";
          return "vendor";
        },
      },
    },
  },
});
