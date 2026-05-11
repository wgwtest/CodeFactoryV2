import { cp, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const sampleName = process.argv[2] || "p2-six-round-sample";
const outDir = resolve(process.argv[3] || `tools/ptest/dist/${sampleName}`);
const sampleFile = resolve(root, `examples/${sampleName}.analysis.json`);

await mkdir(outDir, { recursive: true });
await cp(resolve(root, "templates/report.html"), resolve(outDir, "report.html"));
await cp(resolve(root, "templates/report.css"), resolve(outDir, "report.css"));
await cp(resolve(root, "templates/report.js"), resolve(outDir, "report.js"));
await cp(sampleFile, resolve(outDir, "analysis.json"));

console.log(`P-Test sample report written to ${outDir}/report.html`);
