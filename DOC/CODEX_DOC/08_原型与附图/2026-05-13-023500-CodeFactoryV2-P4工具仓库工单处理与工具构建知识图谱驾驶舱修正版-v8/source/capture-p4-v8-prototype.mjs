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
  ["work-order-processing", "02-1920x1080-P4工单处理-生命周期与工具进展.png"],
  ["tool-building", "03-1920x1080-P4工具构建-匹配生产实时过程值.png"],
  ["asset-cockpit", "04-1920x1080-P4取用驾驶舱-热点冷门与使用热度.png"],
  ["asset-list", "05-1920x1080-P4工具资源列表.png"],
  ["asset-graph", "06-1920x1080-P4覆盖知识图谱.png"],
  ["asset-detail", "07-1920x1080-P4成品工具使用与演进属性.png"],
  ["evolution-actions", "08-1920x1080-P4演进配置深化.png"],
  ["evolution-config-modal", "09-1920x1080-P4演进配置弹窗.png"],
  ["evolution-target-trace", "10-1920x1080-P4被演进对象分支轨迹图.png"],
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });

for (const [state, filename] of shots) {
  await page.goto(`${source}?state=${state}#${state}`, { waitUntil: "networkidle" });
  await page.locator("#p4-v8-stage").waitFor({ state: "visible", timeout: 15000 });
  await page.screenshot({ path: path.join(packageRoot, filename), fullPage: false });
  console.log(`${filename} <= ${source}?state=${state}#${state}`);
}

await browser.close();
