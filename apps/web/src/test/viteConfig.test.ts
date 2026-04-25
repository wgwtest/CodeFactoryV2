// @vitest-environment node

import { resolve } from "node:path";
import { afterEach, describe, expect, test, vi } from "vitest";
import { loadEnv } from "vite";

const originalEnv = { ...process.env };

afterEach(() => {
  vi.resetModules();
  process.env = { ...originalEnv };
});

describe("vite proxy config", () => {
  test("uses repository-root proxy settings with repo-local overrides", async () => {
    delete process.env.VITE_API_PROXY_TARGET;
    delete process.env.VITE_WEB_PORT;
    delete process.env.VITE_WEB_HOST;

    const viteModule = await import("../../vite.config");
    const configFactory = viteModule.default;
    const config = typeof configFactory === "function" ? await configFactory({ command: "serve", mode: "development" }) : configFactory;
    const repoRoot = resolve(process.cwd(), "../..");
    const repoEnv = loadEnv("development", repoRoot, "");
    const expectedProxyTarget = repoEnv.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8020";
    const expectedHost = repoEnv.VITE_WEB_HOST ?? "127.0.0.1";
    const expectedPort = Number.parseInt(repoEnv.VITE_WEB_PORT ?? "5173", 10);

    const apiProxy = config.server?.proxy?.["/api"];

    expect(apiProxy).toMatchObject({ target: expectedProxyTarget });
    expect(config.server?.host).toBe(expectedHost);
    expect(config.server?.port).toBe(Number.isNaN(expectedPort) ? 5173 : expectedPort);
    expect(config.server?.strictPort).toBe(true);
  });
});
