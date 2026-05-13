import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(packageRoot, "../../../..");
const webRequire = createRequire(path.join(repoRoot, "apps/web/package.json"));
const { chromium } = webRequire("@playwright/test");
const source = `file://${path.join(__dirname, "p4-left-object-nav-prototype.html")}`;

const shots = [
  ["demand", "01-1920x1080-P4左侧对象导航-当前叶子需求.png"],
  ["asset", "02-1920x1080-P4左侧对象导航-工具资产说明书.png"],
  ["runtime", "03-1920x1080-P4左侧对象导航-运行观察与自演进.png"],
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });

for (const [state, filename] of shots) {
  await page.goto(`${source}?state=${state}#${state}`, { waitUntil: "networkidle" });
  await page.locator("#p4-v3-stage").waitFor({ state: "visible", timeout: 15000 });
  await page.screenshot({ path: path.join(packageRoot, filename), fullPage: false });
  console.log(`${filename} <= ${source}?state=${state}#${state}`);
}

await browser.close();
