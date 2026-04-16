import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";

describe("vite proxy config", () => {
  test("proxy config keeps mainline default and allows env override", () => {
    const configText = readFileSync(resolve(__dirname, "../../vite.config.ts"), "utf-8");
    expect(configText).toContain("process.env.VITE_API_PROXY_TARGET");
    expect(configText).toContain('?? "http://127.0.0.1:8000"');
  });
});
