import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  envDir: path.resolve(__dirname, "../.."),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          framework: ["react", "react-dom", "react-router-dom", "zustand"],
          motion: ["motion/react"],
          query: ["@tanstack/react-query"],
          charts: ["recharts"],
        },
      },
    },
  },
});
