import { Button } from "antd";

import type { MouseEventHandler } from "react";
import type { P6PlatformLegend } from "../../lib/p6";
import type {
  P6PortalLayoutMode,
  P6PortalProjectionSummary,
  P6PortalRelationshipViewMode,
} from "./p6PortalProjection";

type P6BlueprintLegendProps = {
  archiveName: string;
  legend: P6PlatformLegend;
  projectionSummary: P6PortalProjectionSummary;
  layoutMode: P6PortalLayoutMode;
  relationshipMode: P6PortalRelationshipViewMode;
  hasPersonalLayout: boolean;
  onLayoutModeChange: (mode: P6PortalLayoutMode) => void;
  onRelationshipModeChange: (mode: P6PortalRelationshipViewMode) => void;
  onResetView: MouseEventHandler<HTMLButtonElement>;
};

export function P6BlueprintLegend({
  archiveName,
  legend,
  projectionSummary,
  layoutMode,
  relationshipMode,
  hasPersonalLayout,
  onLayoutModeChange,
  onRelationshipModeChange,
  onResetView,
}: P6BlueprintLegendProps) {
  return (
    <aside id="p6-portal-legend" data-testid="p6-portal-legend" className="p6-blueprint-legend">
      <div className="p6-blueprint-legend__topline">
        <span className="p6-blueprint-legend__badge">图例</span>
        <span className="p6-blueprint-legend__archive">知识库 · {archiveName}</span>
      </div>

      <p className="p6-blueprint-legend__summary">{legend.summary_copy}</p>

      <div className="p6-blueprint-legend__group">
        <div className="p6-blueprint-legend__group-title">上下文</div>
        <div className="p6-blueprint-legend__fact">
          数据源：{projectionSummary.sourceLabel} · {projectionSummary.scenarioLabel}
        </div>
        <div className="p6-blueprint-legend__fact">当前知识库：{projectionSummary.knowledgeBaseName}</div>
        <div className="p6-blueprint-legend__fact">观察提示：{projectionSummary.focusHint}</div>
        <div className="p6-blueprint-legend__fact">场景说明：{projectionSummary.alertMessage}</div>
        {projectionSummary.degradedReason ? (
          <div className="p6-blueprint-legend__fact">降级说明：{projectionSummary.degradedReason}</div>
        ) : null}
      </div>

      <div className="p6-blueprint-legend__group">
        <div className="p6-blueprint-legend__group-title">交互</div>
        {legend.interaction_facts.map((item) => (
          <div key={item} className="p6-blueprint-legend__fact">
            {item}
          </div>
        ))}
      </div>

      <div className="p6-blueprint-legend__group">
        <div className="p6-blueprint-legend__group-title">元素语言</div>
        <div className="p6-blueprint-legend__fact">{legend.element_language_copy}</div>
      </div>

      <div className="p6-blueprint-legend__group">
        <div className="p6-blueprint-legend__group-title">视图控制</div>
        <div className="p6-blueprint-legend__toggle-row">
          <button
            type="button"
            className={["p6-blueprint-legend__toggle", layoutMode === "system" ? "is-active" : ""].filter(Boolean).join(" ")}
            onClick={() => onLayoutModeChange("system")}
          >
            推荐布局
          </button>
          <button
            type="button"
            className={["p6-blueprint-legend__toggle", layoutMode === "personal" ? "is-active" : ""].filter(Boolean).join(" ")}
            onClick={() => onLayoutModeChange("personal")}
            disabled={!hasPersonalLayout}
          >
            个人布局
          </button>
        </div>
        <div className="p6-blueprint-legend__toggle-row">
          <button
            type="button"
            className={[
              "p6-blueprint-legend__toggle",
              relationshipMode === "semantic" ? "is-active" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => onRelationshipModeChange("semantic")}
          >
            语义线
          </button>
          <button
            type="button"
            className={[
              "p6-blueprint-legend__toggle",
              relationshipMode === "projection" ? "is-active" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => onRelationshipModeChange("projection")}
          >
            投影聚合
          </button>
        </div>
      </div>

      <div className="p6-blueprint-legend__group">
        <div className="p6-blueprint-legend__group-title">投影摘要</div>
        <div className="p6-blueprint-legend__facts-grid">
          <span className="p6-blueprint-legend__fact-chip">系统 {projectionSummary.moduleCount}</span>
          <span className="p6-blueprint-legend__fact-chip">角色 {projectionSummary.userCount}</span>
          <span className="p6-blueprint-legend__fact-chip">产物 {projectionSummary.artifactCount}</span>
          <span className="p6-blueprint-legend__fact-chip">连线 {projectionSummary.flowCount}</span>
          <span className="p6-blueprint-legend__fact-chip">自动 {projectionSummary.autoProjectionCount}</span>
          <span className="p6-blueprint-legend__fact-chip">人工 {projectionSummary.manualProjectionCount}</span>
        </div>
        <div className="p6-blueprint-legend__fact">当前布局：{projectionSummary.layoutModeLabel}</div>
        <div className="p6-blueprint-legend__fact">关系视图：{projectionSummary.relationshipModeLabel}</div>
        <div className="p6-blueprint-legend__fact">数据新鲜度：{projectionSummary.freshnessLabel}</div>
        <div className="p6-blueprint-legend__fact">观察上下文：{projectionSummary.contextHint}</div>
      </div>

      <div className="p6-blueprint-legend__group">
        <div className="p6-blueprint-legend__group-title">流向标记</div>
        <ul className="p6-blueprint-legend__signals">
          {legend.signal_items.map((item) => (
            <li key={item.label}>
              <span className={`p6-blueprint-legend__signal-dot p6-blueprint-legend__signal-dot--${item.tone}`} />
              <span>{item.label}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="p6-blueprint-legend__group">
        <div className="p6-blueprint-legend__group-title">平台注释</div>
        <ul className="p6-blueprint-legend__roadmap">
          {legend.roadmap_items.map((item) => (
            <li key={item.item_id}>
              <span>{item.label}</span>
              <strong>{item.status}</strong>
            </li>
          ))}
        </ul>
      </div>

      <div className="p6-blueprint-legend__footer">
        <Button className="p6-blueprint-legend__reset" onClick={onResetView}>
          重置视图
        </Button>
      </div>
    </aside>
  );
}
