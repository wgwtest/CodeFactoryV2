import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require("../../../../../apps/web/node_modules/@playwright/test");
const html = path.join(__dirname, "p3-design-workspace-canvas-poc.html");
const url = `file://${html}`;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(url);

await page.locator("#mainCanvas").waitFor();
const initialZoom = await page.locator("#zoomHud").textContent();
const initialPan = await page.locator("#panHud").textContent();
const initialSelection = await page.locator("#selStage").textContent();

await page.locator("#wideBtn").click();
const wideSelection = await page.locator("#selStage").textContent();
const wideZoom = await page.locator("#zoomHud").textContent();

const canvasBox = await page.locator("#mainCanvas").boundingBox();
if (!canvasBox) throw new Error("mainCanvas missing");
await page.mouse.move(canvasBox.x + 500, canvasBox.y + 380);
await page.mouse.down();
await page.mouse.move(canvasBox.x + 250, canvasBox.y + 440, { steps: 8 });
await page.mouse.up();
const draggedPan = await page.locator("#panHud").textContent();

await page.mouse.move(canvasBox.x + 580, canvasBox.y + 360);
await page.mouse.wheel(0, -600);
const zoomed = await page.locator("#zoomHud").textContent();

await page.locator("#nextBtn").click();
const afterNext = await page.locator("#windowPill").textContent();

const checks = [
  ["初始选中软设文档", initialSelection?.includes("软设文档")],
  ["定位大型架构图", wideSelection?.includes("分层架构")],
  ["大型图缩放低于初始", wideZoom !== initialZoom],
  ["拖拽改变平移值", draggedPan !== initialPan],
  ["滚轮改变缩放值", zoomed !== wideZoom],
  ["下一窗口更新滑窗文案", afterNext?.includes("分层架构")]
];

const failed = checks.filter(([, ok]) => !ok);
if (failed.length) {
  console.error("Canvas PoC verification failed:");
  for (const [name] of failed) console.error(`- ${name}`);
  await browser.close();
  process.exit(1);
}

console.log("Canvas PoC verification passed:");
for (const [name] of checks) console.log(`- ${name}`);
console.log(`initialZoom=${initialZoom}; wideZoom=${wideZoom}; zoomed=${zoomed}`);
console.log(`initialPan=${initialPan}; draggedPan=${draggedPan}`);
console.log(`afterNext=${afterNext}`);

await browser.close();
