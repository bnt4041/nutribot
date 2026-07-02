import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/admin/",
  plugins: [react()],
  build: {
    assetsInlineLimit: 0, // nunca convertir assets a base64 inline
  },
  server: {
    host: "0.0.0.0",
    port: 5174,
    watch: { usePolling: true },
  },
});
