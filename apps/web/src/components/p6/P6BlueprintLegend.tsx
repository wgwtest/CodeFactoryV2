import { Button } from "antd";

import type { MouseEventHandler } from "react";
import { p6PortalLegendRoadmap } from "./p6PortalData";
import type {
  P6PortalLayoutMode,
  P6PortalProjectionSummary,
  P6PortalRelationshipViewMode,
} from "./p6PortalProjection";

type P6BlueprintLegendProps = {
  archiveName: string;
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

      <p className="p6-blueprint-legend__summary">门户只负责导览与跳转，不承载业务编辑。双击节点即可进入对应模块。</p>

      <div className="p6-blueprint-legend__group">
        <div className="p6-blueprint-legend__group-title">交互</div>
        <div className="p6-blueprint-legend__fact">单击高亮 / 双击进入 / 滚轮缩放 / 背景平移</div>
        <div className="p6-blueprint-legend__fact">节点拖拽仅在自动布局区内生效，超界后自动回收</div>
      </div>

      <div className="p6-blueprint-legend__group">
        <div className="p6-blueprint-legend__group-title">元素语言</div>
        <div className="p6-blueprint-legend__fact">圆角卡片 = 系统节点，椭圆胶囊 = 角色节点，小胶囊 = 数据产物</div>
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
      </div>

      <div className="p6-blueprint-legend__group">
        <div className="p6-blueprint-legend__group-title">流向标记</div>
        <ul className="p6-blueprint-legend__signals">
          <li>
            <span className="p6-blueprint-legend__signal-dot p6-blueprint-legend__signal-dot--knowledge" />
            <span>知识供给</span>
          </li>
          <li>
            <span className="p6-blueprint-legend__signal-dot p6-blueprint-legend__signal-dot--analysis" />
            <span>需求分析</span>
          </li>
          <li>
            <span className="p6-blueprint-legend__signal-dot p6-blueprint-legend__signal-dot--design" />
            <span>设计转化</span>
          </li>
          <li>
            <span className="p6-blueprint-legend__signal-dot p6-blueprint-legend__signal-dot--tooling" />
            <span>工具匹配</span>
          </li>
          <li>
            <span className="p6-blueprint-legend__signal-dot p6-blueprint-legend__signal-dot--delivery" />
            <span>构建执行</span>
          </li>
        </ul>
      </div>

      <div className="p6-blueprint-legend__group">
        <div className="p6-blueprint-legend__group-title">平台注释</div>
        <ul className="p6-blueprint-legend__roadmap">
          {p6PortalLegendRoadmap.map((item) => (
            <li key={item.id}>
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
