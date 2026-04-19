// @vitest-environment node

import { afterEach, describe, expect, test, vi } from "vitest";

const originalEnv = { ...process.env };

afterEach(() => {
  vi.resetModules();
  process.env = { ...originalEnv };
});

describe("vite proxy config", () => {
  test("uses repository-root proxy settings with stable local defaults", async () => {
    delete process.env.VITE_API_PROXY_TARGET;
    delete process.env.VITE_WEB_PORT;
    delete process.env.VITE_WEB_HOST;

    const viteModule = await import("../../vite.config");
    const configFactory = viteModule.default;
    const config = typeof configFactory === "function" ? await configFactory({ command: "serve", mode: "development" }) : configFactory;

    expect(config.server?.proxy?.["/api"].target).toBe("http://127.0.0.1:8020");
    expect(config.server?.host).toBe("127.0.0.1");
    expect(config.server?.port).toBe(5173);
    expect(config.server?.strictPort).toBe(true);
  });
});
