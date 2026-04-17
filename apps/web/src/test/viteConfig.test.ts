import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";

describe("vite proxy config", () => {
  test("proxy config keeps p4 default ports and allows env override", () => {
    const configText = readFileSync(resolve(__dirname, "../../vite.config.ts"), "utf-8");
    expect(configText).toContain("process.env.VITE_API_PROXY_TARGET");
    expect(configText).toContain('?? "http://127.0.0.1:8010"');
    expect(configText).toContain("process.env.VITE_WEB_PORT");
    expect(configText).toContain('?? "5180"');
    expect(configText).toContain("strictPort: true");
  });
});
