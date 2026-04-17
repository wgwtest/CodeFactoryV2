import { Button } from "antd";

import type { MouseEventHandler } from "react";
import { p6PortalLegendRoadmap } from "./p6PortalData";

type P6BlueprintLegendProps = {
  archiveName: string;
  onResetView: MouseEventHandler<HTMLButtonElement>;
};

export function P6BlueprintLegend({ archiveName, onResetView }: P6BlueprintLegendProps) {
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
