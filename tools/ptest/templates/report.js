const palette = ["#2458a6", "#b44b2d", "#267a58", "#7a4aa0", "#9b6a19", "#3f6f77"];

const nodes = {
  loadInput: document.querySelector("#analysis-file"),
  loadStatus: document.querySelector("#load-status"),
  overview: document.querySelector("#overview"),
  metrics: document.querySelector("#metrics"),
  timeline: document.querySelector("#timeline"),
  evidence: document.querySelector("#evidence"),
};

boot();

async function boot() {
  nodes.loadInput.addEventListener("change", handleFileSelection);

  const embeddedAnalysis = document.querySelector("#embedded-analysis");
  if (embeddedAnalysis?.textContent?.trim()) {
    try {
      renderDataset(JSON.parse(embeddedAnalysis.textContent), "已读取内嵌 analysis.json");
      return;
    } catch (error) {
      nodes.loadStatus.textContent = `内嵌 analysis.json 读取失败：${error.message}`;
    }
  }

  try {
    const response = await fetch("./analysis.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`analysis.json HTTP ${response.status}`);
    }
    renderDataset(await response.json(), "已读取同目录 analysis.json");
  } catch (error) {
    nodes.loadStatus.textContent = "未自动读取 analysis.json，可手动选择 JSON 文件。";
  }
}

async function handleFileSelection(event) {
  const [file] = event.target.files;
  if (!file) {
    return;
  }

  try {
    renderDataset(JSON.parse(await file.text()), `已载入 ${file.name}`);
  } catch (error) {
    nodes.loadStatus.textContent = `JSON 读取失败：${error.message}`;
  }
}

function renderDataset(dataset, statusText) {
  const validation = validateAnalysisDataset(dataset);
  if (validation.errors.length > 0) {
    nodes.loadStatus.textContent = `analysis.json 结构错误：${validation.errors.join("；")}`;
    return;
  }

  nodes.loadStatus.textContent = statusText;
  document.title = `${dataset.title} | P-Test`;
  renderOverview(dataset);
  renderMetrics(dataset);
  renderTimeline(dataset);
  renderEvidence(dataset);
}

function renderOverview(dataset) {
  const metrics = dataset.metrics || [];
  const trendCount = metrics.filter((metric) => chooseChartKind(metric) === "line").length;
  const distributionCount = metrics.filter((metric) => chooseChartKind(metric) === "distribution").length;
  const statusCount = metrics.filter((metric) => chooseChartKind(metric) === "status").length;

  nodes.overview.innerHTML = `
    <div class="report-title">
      <p class="kicker">P-Test / static analysis report</p>
      <h1>${escapeHtml(dataset.title)}</h1>
      <p>${escapeHtml(dataset.conclusions[0] || "固定模板读取 analysis.json，按指标定义渲染分析结果。")}</p>
    </div>
    <div class="summary-grid">
      ${summaryCell("测试对象", dataset.test_objects.length)}
      ${summaryCell("测试轮次", dataset.iterations.length)}
      ${summaryCell("指标总数", metrics.length)}
      ${summaryCell("折线趋势", trendCount)}
      ${summaryCell("分布图", distributionCount)}
      ${summaryCell("状态矩阵", statusCount)}
    </div>
    <section class="analysis-method">
      <h2>分析输入</h2>
      <dl>
        <div><dt>计划来源</dt><dd>${linkToPath(dataset.plan_ref, dataset.plan_ref)}</dd></div>
        <div><dt>生成时间</dt><dd>${escapeHtml(dataset.generated_at)}</dd></div>
        <div><dt>执行模式</dt><dd>${escapeHtml(dataset.analysis_method.mode)}</dd></div>
      </dl>
      <ol>${(dataset.analysis_method.notes || []).map((note) => `<li>${escapeHtml(note)}</li>`).join("")}</ol>
    </section>
  `;
}

function summaryCell(label, value) {
  return `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function renderMetrics(dataset) {
  nodes.metrics.innerHTML = buildMetricPanels(dataset).map((panel, index) => renderMetricPanel(dataset, panel, index)).join("");
}

function renderMetricPanel(dataset, panel, index) {
  const chartKind = chooseChartKind(panel.metric);
  const chart = renderChart(dataset, panel, chartKind);

  return `
    <article class="metric-panel">
      <header class="metric-header">
        <div>
          <p>${escapeHtml(panel.metric.metric_id)}</p>
          <h3>${escapeHtml(panel.metric.name)}</h3>
        </div>
        <div class="metric-badges">
          <span>${escapeHtml(panel.metric.type)}</span>
          <span>${escapeHtml(panel.metric.visualization)}</span>
        </div>
      </header>
      <div class="metric-body">
        <div class="chart-shell chart-${chartKind}">
          ${chart}
        </div>
        <aside class="metric-meta">
          <dl>
            <div><dt>展示形式</dt><dd>${chartKindLabel(chartKind)}</dd></div>
            <div><dt>数据来源</dt><dd>${escapeHtml(panel.metric.source)}</dd></div>
            <div><dt>计算口径</dt><dd>${escapeHtml(panel.metric.calculation)}</dd></div>
            <div><dt>指标局限</dt><dd>${escapeHtml(panel.metric.limitations)}</dd></div>
          </dl>
        </aside>
      </div>
      ${renderLatestTable(dataset, panel, index)}
    </article>
  `;
}

function renderChart(dataset, panel, chartKind) {
  if (chartKind === "line") {
    return renderLineChart(dataset, panel);
  }
  if (chartKind === "bar") {
    return renderBarChart(dataset, panel);
  }
  if (chartKind === "status") {
    return renderStatusMatrix(dataset, panel);
  }
  if (chartKind === "distribution") {
    return renderDistribution(dataset, panel);
  }
  return renderDataTable(dataset, panel);
}

function renderLineChart(dataset, panel) {
  const numericValues = getNumericValues(panel);
  const max = Math.max(...numericValues, 1);
  const min = Math.min(...numericValues, 0);
  const range = Math.max(max - min, 1);
  const width = 640;
  const height = 220;
  const padding = { top: 18, right: 24, bottom: 34, left: 48 };
  const xStep = panel.iterations.length > 1
    ? (width - padding.left - padding.right) / (panel.iterations.length - 1)
    : 0;

  const lines = panel.series.map((entry, seriesIndex) => {
    const points = panel.iterations.map((iteration, pointIndex) => {
      const value = entry.points.find((point) => point.iteration === iteration)?.value;
      if (typeof value !== "number") {
        return null;
      }
      const x = padding.left + pointIndex * xStep;
      const y = padding.top + ((max - value) / range) * (height - padding.top - padding.bottom);
      return { x, y, value, iteration };
    }).filter(Boolean);
    const path = points.map((point, pointIndex) => `${pointIndex === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
    const color = palette[seriesIndex % palette.length];
    return `
      <path d="${path}" fill="none" stroke="${color}" stroke-width="2.5" />
      ${points.map((point) => `<circle cx="${point.x}" cy="${point.y}" r="4" fill="${color}"><title>R${point.iteration}: ${formatMetricValue(point.value, panel.metric)}</title></circle>`).join("")}
    `;
  }).join("");

  return `
    <svg class="line-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeAttribute(panel.metric.name)}趋势折线图">
      ${[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
        const y = padding.top + ratio * (height - padding.top - padding.bottom);
        const value = max - ratio * range;
        return `<line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" class="grid-line" /><text x="8" y="${y + 4}" class="axis-label">${formatAxisValue(value)}</text>`;
      }).join("")}
      ${panel.iterations.map((iteration, pointIndex) => {
        const x = padding.left + pointIndex * xStep;
        return `<text x="${x}" y="${height - 10}" class="axis-label" text-anchor="middle">R${iteration}</text>`;
      }).join("")}
      ${lines}
    </svg>
    ${renderLegend(dataset, panel)}
  `;
}

function renderBarChart(dataset, panel) {
  const values = getNumericValues(panel);
  const max = Math.max(...values, 1);
  return `
    <div class="bar-chart">
      ${panel.series.map((entry, seriesIndex) => `
        <section>
          <h4><i style="background:${palette[seriesIndex % palette.length]}"></i>${escapeHtml(getObjectName(dataset, entry.object_id))}</h4>
          <div class="bar-row" style="--count:${panel.iterations.length}">
            ${panel.iterations.map((iteration) => {
              const value = entry.points.find((point) => point.iteration === iteration)?.value;
              const height = typeof value === "number" ? Math.max((value / max) * 100, 4) : 4;
              return `<div><span style="height:${height}%;background:${palette[seriesIndex % palette.length]}"></span><b>${formatMetricValue(value, panel.metric)}</b><em>R${iteration}</em></div>`;
            }).join("")}
          </div>
        </section>
      `).join("")}
    </div>
  `;
}

function renderStatusMatrix(dataset, panel) {
  return `
    <table class="status-table">
      <thead><tr><th>对象</th>${panel.iterations.map((iteration) => `<th>R${iteration}</th>`).join("")}</tr></thead>
      <tbody>
        ${panel.series.map((entry) => `
          <tr>
            <th>${escapeHtml(getObjectName(dataset, entry.object_id))}</th>
            ${panel.iterations.map((iteration) => {
              const value = entry.points.find((point) => point.iteration === iteration)?.value;
              return `<td><span class="status-pill ${value ? "ok" : "bad"}">${formatMetricValue(value, panel.metric)}</span></td>`;
            }).join("")}
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderDistribution(dataset, panel) {
  const categories = Array.from(new Set(panel.series.flatMap((entry) =>
    entry.points.flatMap((point) => Object.keys(point.value || {})),
  )));

  return `
    <div class="distribution-chart">
      ${panel.series.flatMap((entry, seriesIndex) => entry.points.map((point) => {
        const total = Object.values(point.value || {}).reduce((sum, value) => sum + Number(value || 0), 0) || 1;
        return `
          <section>
            <h4>${escapeHtml(getObjectName(dataset, entry.object_id))} / R${point.iteration}</h4>
            <div class="stacked-bar">
              ${categories.map((category, categoryIndex) => {
                const value = Number(point.value?.[category] || 0);
                const width = (value / total) * 100;
                return `<span style="width:${width}%;background:${palette[categoryIndex % palette.length]}"><b>${value}</b></span>`;
              }).join("")}
            </div>
          </section>
        `;
      })).join("")}
      <div class="legend">${categories.map((category, index) => `<span><i style="background:${palette[index % palette.length]}"></i>${escapeHtml(category)}</span>`).join("")}</div>
    </div>
  `;
}

function renderDataTable(dataset, panel) {
  return `
    <table class="data-table">
      <thead><tr><th>对象</th>${panel.iterations.map((iteration) => `<th>R${iteration}</th>`).join("")}</tr></thead>
      <tbody>
        ${panel.series.map((entry) => `<tr><th>${escapeHtml(getObjectName(dataset, entry.object_id))}</th>${panel.iterations.map((iteration) => `<td>${formatMetricValue(entry.points.find((point) => point.iteration === iteration)?.value, panel.metric)}</td>`).join("")}</tr>`).join("")}
      </tbody>
    </table>
  `;
}

function renderLatestTable(dataset, panel, index) {
  const latestIteration = Math.max(...panel.iterations);
  return `
    <table class="latest-table">
      <caption>最新轮次 R${latestIteration} 数据切片</caption>
      <thead><tr><th>对象</th><th>最新值</th><th>序列</th></tr></thead>
      <tbody>
        ${panel.series.map((entry, seriesIndex) => {
          const latest = entry.points.find((point) => point.iteration === latestIteration)?.value;
          return `<tr><th><i style="background:${palette[seriesIndex % palette.length]}"></i>${escapeHtml(getObjectName(dataset, entry.object_id))}</th><td>${formatMetricValue(latest, panel.metric)}</td><td>${entry.points.map((point) => formatCompactValue(point.value)).join(" / ")}</td></tr>`;
        }).join("")}
      </tbody>
    </table>
  `;
}

function renderLegend(dataset, panel) {
  return `<div class="legend">${panel.series.map((entry, index) => `<span><i style="background:${palette[index % palette.length]}"></i>${escapeHtml(getObjectName(dataset, entry.object_id))}</span>`).join("")}</div>`;
}

function renderTimeline(dataset) {
  nodes.timeline.innerHTML = dataset.timeline.map((item) => `
    <article class="timeline-item">
      <span>R${item.iteration}</span>
      <div>
        <h3>${escapeHtml(item.title)}</h3>
        <p><strong>问题</strong>${escapeHtml(item.problem)}</p>
        <p><strong>整改</strong>${escapeHtml(item.change)}</p>
        <p><strong>结论</strong>${escapeHtml(item.result)}</p>
      </div>
    </article>
  `).join("");
}

function renderEvidence(dataset) {
  nodes.evidence.innerHTML = dataset.evidence_index.map((item) => `
    <a class="evidence-link" href="${escapeAttribute(item.path)}">
      <span>${escapeHtml(item.type)}</span>
      <strong>${escapeHtml(item.label)}</strong>
      <em>${escapeHtml(item.path)}</em>
    </a>
  `).join("");
}

function getNumericValues(panel) {
  return panel.series.flatMap((entry) =>
    entry.points.map((point) => point.value).filter((value) => typeof value === "number"),
  );
}

function chooseChartKind(metric) {
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

function chartKindLabel(kind) {
  return {
    line: "折线趋势图",
    bar: "柱状对比图",
    status: "状态矩阵",
    distribution: "分布图",
    table: "数据表",
  }[kind] || kind;
}

function validateAnalysisDataset(dataset) {
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

function buildMetricPanels(dataset) {
  const seriesByMetric = groupBy(dataset.series || [], "metric_id");

  return (dataset.metrics || []).map((metric) => {
    const metricSeries = seriesByMetric.get(metric.metric_id) || [];
    const iterations = Array.from(
      new Set(metricSeries.flatMap((entry) => entry.points.map((point) => point.iteration))),
    ).sort((a, b) => a - b);

    return { metric, series: metricSeries, iterations };
  });
}

function formatMetricValue(value, metric) {
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
  if (typeof value === "object") {
    return Object.entries(value).map(([key, entryValue]) => `${key}:${entryValue}`).join(" / ");
  }
  return String(value);
}

function formatCompactValue(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "boolean") {
    return value ? "Y" : "N";
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toLocaleString("en-US") : value.toFixed(1);
  }
  if (typeof value === "object") {
    return Object.values(value).join(":");
  }
  return String(value);
}

function formatAxisValue(value) {
  if (Math.abs(value) >= 1000) {
    return `${Math.round(value / 100) / 10}k`;
  }
  return `${Math.round(value * 10) / 10}`;
}

function getObjectName(dataset, objectId) {
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

function linkToPath(path, label) {
  return `<a href="${escapeAttribute(path)}">${escapeHtml(label)}</a>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#96;");
}
