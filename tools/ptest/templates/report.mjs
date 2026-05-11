export function validateAnalysisDataset(dataset) {
  const errors = [];
  const requiredFields = [
    "schema_version",
    "title",
    "plan_ref",
    "generated_at",
    "analysis_method",
    "test_objects",
    "iterations",
    "metrics",
    "series",
    "timeline",
    "evidence_index",
    "conclusions",
  ];

  if (!dataset || typeof dataset !== "object") {
    return { errors: ["dataset must be an object"] };
  }

  for (const field of requiredFields) {
    if (!(field in dataset)) {
      errors.push(`missing required field: ${field}`);
    }
  }

  if (dataset.schema_version !== "ptest.analysis.v1") {
    errors.push("schema_version must be ptest.analysis.v1");
  }

  for (const field of ["test_objects", "iterations", "metrics", "series", "timeline", "evidence_index", "conclusions"]) {
    if (field in dataset && !Array.isArray(dataset[field])) {
      errors.push(`${field} must be an array`);
    }
  }

  const objectIds = new Set((dataset.test_objects || []).map((item) => item.object_id));
  const metricIds = new Set((dataset.metrics || []).map((item) => item.metric_id));
  const iterationIds = new Set((dataset.iterations || []).map((item) => item.iteration));

  for (const item of dataset.series || []) {
    if (!metricIds.has(item.metric_id)) {
      errors.push(`series references unknown metric_id: ${item.metric_id}`);
    }
    if (!objectIds.has(item.object_id)) {
      errors.push(`series references unknown object_id: ${item.object_id}`);
    }
    if (!Array.isArray(item.points)) {
      errors.push(`series ${item.metric_id}/${item.object_id} points must be an array`);
      continue;
    }
    for (const point of item.points) {
      if (!iterationIds.has(point.iteration)) {
        errors.push(`series ${item.metric_id}/${item.object_id} references unknown iteration: ${point.iteration}`);
      }
    }
  }

  return { errors };
}

export function buildMetricPanels(dataset) {
  const seriesByMetric = groupBy(dataset.series || [], "metric_id");

  return (dataset.metrics || []).map((metric) => {
    const metricSeries = seriesByMetric.get(metric.metric_id) || [];
    const iterations = Array.from(
      new Set(metricSeries.flatMap((entry) => entry.points.map((point) => point.iteration))),
    ).sort((a, b) => a - b);

    return {
      metric,
      series: metricSeries,
      iterations,
    };
  });
}

export function formatMetricValue(value, metric) {
  if (value === null || value === undefined) {
    return "缺失";
  }

  if (metric.type === "boolean") {
    return value ? "是" : "否";
  }

  if (typeof value === "number") {
    const rendered = Number.isInteger(value) ? value.toLocaleString("en-US") : value.toFixed(2);
    return metric.unit ? `${rendered} ${metric.unit}` : rendered;
  }

  return String(value);
}

export function chooseChartKind(metric) {
  if (metric.type === "boolean" || metric.visualization === "status_matrix") {
    return "status";
  }
  if (metric.type === "category" || metric.visualization === "stacked_bar") {
    return "distribution";
  }
  if (metric.visualization === "bar") {
    return "bar";
  }
  if (metric.visualization === "trend" || metric.type === "score" || metric.type === "ratio" || metric.type === "count") {
    return "line";
  }
  return "table";
}

export function getObjectName(dataset, objectId) {
  return (dataset.test_objects || []).find((item) => item.object_id === objectId)?.display_name || objectId;
}

function groupBy(items, key) {
  const grouped = new Map();
  for (const item of items) {
    const value = item[key];
    if (!grouped.has(value)) {
      grouped.set(value, []);
    }
    grouped.get(value).push(item);
  }
  return grouped;
}
