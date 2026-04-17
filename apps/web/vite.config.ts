import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8030";
const webPort = Number.parseInt(process.env.VITE_WEB_PORT ?? "5174", 10);

export default defineConfig({
  plugins: [react()],
  server: {
    host: process.env.VITE_WEB_HOST ?? "127.0.0.1",
    port: Number.isNaN(webPort) ? 5174 : webPort,
    strictPort: true,
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true
      }
    }
  },
  test: {
    include: ["src/test/**/*.test.ts?(x)"],
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts"
  }
});
