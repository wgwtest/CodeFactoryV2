import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

import {
  buildMetricPanels,
  chooseChartKind,
  formatMetricValue,
  validateAnalysisDataset,
} from "../templates/report.mjs";

const sample = JSON.parse(
  await readFile(new URL("../examples/p2-six-round-sample.analysis.json", import.meta.url), "utf8"),
);

test("sample analysis dataset satisfies the required v1 structure", () => {
  const result = validateAnalysisDataset(sample);

  assert.deepEqual(result.errors, []);
  assert.equal(sample.schema_version, "ptest.analysis.v1");
  assert.ok(sample.metrics.length >= 13);
  assert.ok(sample.series.length >= sample.metrics.length);
});

test("metric panels are organized by metric instead of test object", () => {
  const panels = buildMetricPanels(sample);
  const completedTurns = panels.find((panel) => panel.metric.metric_id === "completed_turns");

  assert.ok(completedTurns);
  assert.deepEqual(
    completedTurns.series.map((entry) => entry.object_id).sort(),
    ["brainstorm-v1", "brainstorm-v1-dify-workflow"],
  );
  assert.deepEqual(completedTurns.iterations, [1, 2, 3, 4, 5, 6]);
});

test("metric value formatting handles common P-Test metric types", () => {
  assert.equal(formatMetricValue(true, { type: "boolean", unit: "是/否" }), "是");
  assert.equal(formatMetricValue(false, { type: "boolean", unit: "是/否" }), "否");
  assert.equal(formatMetricValue(1234, { type: "count", unit: "字" }), "1,234 字");
  assert.equal(formatMetricValue(null, { type: "count", unit: "次" }), "缺失");
});

test("chart kind follows analysis visualization and metric type", () => {
  assert.equal(chooseChartKind({ type: "count", visualization: "trend" }), "line");
  assert.equal(chooseChartKind({ type: "count", visualization: "bar" }), "bar");
  assert.equal(chooseChartKind({ type: "boolean", visualization: "status_matrix" }), "status");
  assert.equal(chooseChartKind({ type: "category", visualization: "stacked_bar" }), "distribution");
});
