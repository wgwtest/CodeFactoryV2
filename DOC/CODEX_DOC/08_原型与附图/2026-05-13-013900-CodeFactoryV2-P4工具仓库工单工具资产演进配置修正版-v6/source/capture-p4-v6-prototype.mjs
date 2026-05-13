import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(packageRoot, "../../../..");
const webRequire = createRequire(path.join(repoRoot, "apps/web/package.json"));
const { chromium } = webRequire("@playwright/test");
const source = `file://${path.join(__dirname, "p4-object-workspace-deepened-prototype.html")}`;

const shots = [
  ["demand-sheets", "01-1920x1080-P4工单池-工单-工具递进.png"],
  ["demand-tool-config", "02-1920x1080-P4单工具匹配策略交付约束版本控制.png"],
  ["asset-list", "03-1920x1080-P4工具资产四种展示形态.png"],
  ["asset-detail", "04-1920x1080-P4成品工具使用与演进属性.png"],
  ["evolution-actions", "05-1920x1080-P4演进配置深化.png"],
  ["evolution-target-trace", "06-1920x1080-P4被演进对象分支轨迹图.png"],
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });

for (const [state, filename] of shots) {
  await page.goto(`${source}?state=${state}#${state}`, { waitUntil: "networkidle" });
  await page.locator("#p4-v6-stage").waitFor({ state: "visible", timeout: 15000 });
  await page.screenshot({ path: path.join(packageRoot, filename), fullPage: false });
  console.log(`${filename} <= ${source}?state=${state}#${state}`);
}

await browser.close();
