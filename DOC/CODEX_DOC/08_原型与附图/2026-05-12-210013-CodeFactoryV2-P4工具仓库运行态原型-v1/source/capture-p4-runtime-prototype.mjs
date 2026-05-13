import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(packageRoot, "../../../..");
const webRequire = createRequire(path.join(repoRoot, "apps/web/package.json"));
const { chromium } = webRequire("@playwright/test");
const baseUrl = process.env.P4_PROTO_BASE_URL ?? "http://127.0.0.1:5180";

const shots = [
  {
    name: "01-1920x1080-P4总览态.png",
    url: "/xx-p4",
    ready: "#xx-p4-overview-pane",
  },
  {
    name: "02-1920x1080-P4输入工序链态.png",
    url: "/xx-p4",
    click: "#xx-p4-workspace-tab-input-chain",
    ready: "#xx-p4-input-chain-workspace",
  },
  {
    name: "03-1920x1080-P4自演进巡检态.png",
    url: "/xx-p4",
    click: "#xx-p4-workspace-tab-evolution",
    ready: "#xx-p4-evolution-workspace",
  },
  {
    name: "04-1920x1080-P4工具仓库与真实交付态.png",
    url: "/xx-p4",
    click: "#xx-p4-workspace-tab-registry",
    ready: "#xx-p4-registry-pane",
  },
  {
    name: "05-1920x1080-P3提交P4工具需求态.png",
    url: "/xx-p3-sim",
    ready: "#xx-p3-page",
  },
  {
    name: "06-1920x1080-P5消费P4供给态.png",
    url: "/xx-p5-sim",
    ready: "#xx-p5-page",
    prepare: async (page) => {
      await page.locator("#xx-p5-sheet-id-input").fill(process.env.P4_PROTO_SHEET_ID ?? "tds-24deb7661568");
      await page.getByRole("button", { name: "查询整单" }).click();
      await page.locator("#xx-p5-sheet-items").waitFor({ state: "visible", timeout: 15000 });
      await page.locator("#xx-p5-item-id-input").fill(process.env.P4_PROTO_ITEM_ID ?? "tdi-ab8e557bcbb1");
      await page.getByRole("button", { name: "刷新进度" }).click();
      await page.locator("#xx-p5-progress-card").waitFor({ state: "visible", timeout: 15000 });
      await page.locator("#xx-p5-progress-card").scrollIntoViewIfNeeded();
    },
  },
  {
    name: "07-1920x1080-P4供给模拟输出态.png",
    url: "/xx-p4-supply-sim",
    ready: "text=P4 供给模拟输出台",
  },
  {
    name: "08-1920x1080-P4逻辑关系图.png",
    url: `file://${path.join(__dirname, "p4-runtime-prototype-map.html")}`,
    ready: "#p4-runtime-prototype-map",
  },
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });

for (const shot of shots) {
  const targetUrl = shot.url.startsWith("file://") ? shot.url : new URL(shot.url, baseUrl).toString();
  await page.goto(targetUrl, { waitUntil: "networkidle" });
  if (shot.click) {
    await page.locator(shot.click).click();
  }
  await page.locator(shot.ready).waitFor({ state: "visible", timeout: 15000 });
  if (shot.prepare) {
    await shot.prepare(page);
  }
  await page.waitForTimeout(600);
  await page.screenshot({
    path: path.join(packageRoot, shot.name),
    fullPage: false,
  });
  console.log(`${shot.name} <= ${targetUrl}`);
}

await browser.close();
