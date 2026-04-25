import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

const repoRoot = resolve(__dirname, "../..");

export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, repoRoot, ""), ...process.env };
  const apiProxyTarget = env.VITE_API_PROXY_TARGET ?? env.VITE_DEV_API_PROXY_TARGET ?? "http://127.0.0.1:8020";
  const webPort = Number.parseInt(env.VITE_WEB_PORT ?? "5173", 10);

  return {
    envDir: repoRoot,
    plugins: [react()],
    server: {
      host: env.VITE_WEB_HOST ?? "127.0.0.1",
      port: Number.isNaN(webPort) ? 5173 : webPort,
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
  };
});
