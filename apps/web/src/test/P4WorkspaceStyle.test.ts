import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";

describe("p4 workspace visual tokens", () => {
  test("uses solid morandi active tones for segmented workspace tabs", () => {
    const cssText = readFileSync(resolve(__dirname, "../components/p4/p4-page.css"), "utf-8");

    expect(cssText).toContain(".xx-p4-workspace-tabs > .ant-tabs-nav .ant-tabs-tab-active .xx-p4-workspace-tab-card");
    expect(cssText).toContain("background: var(--workspace-active-surface");
    expect(cssText).not.toContain("background: linear-gradient(180deg, var(--workspace-active-surface");

    expect(cssText).toContain("--workspace-accent: #6f8fb1");
    expect(cssText).toContain("--workspace-accent: #7f9b76");
    expect(cssText).toContain("--workspace-accent: #a06d74");
    expect(cssText).toContain("--workspace-accent: #8978a8");
  });
});
