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
      <div className="p6-blueprint-legend__eyebrow">P6 平台入口层</div>
      <h2 className="p6-blueprint-legend__title">P6.1 门户蓝图画布</h2>
      <p className="p6-blueprint-legend__summary">
        统一入口负责感知平台运行态势、引导用户进入正确模块，并为后续登录与权限层预留稳定位置。
      </p>

      <div className="p6-blueprint-legend__group">
        <div className="p6-blueprint-legend__group-title">当前上下文</div>
        <div className="p6-blueprint-legend__fact">知识库：{archiveName}</div>
        <div className="p6-blueprint-legend__fact">交互：单击高亮 / 双击进入 / 滚轮缩放 / 背景平移</div>
      </div>

      <div className="p6-blueprint-legend__group">
        <div className="p6-blueprint-legend__group-title">P6 占位路线</div>
        <ul className="p6-blueprint-legend__roadmap">
          {p6PortalLegendRoadmap.map((item) => (
            <li key={item.id}>
              <span>{item.label}</span>
              <strong>{item.status}</strong>
            </li>
          ))}
        </ul>
      </div>

      <Button className="p6-blueprint-legend__reset" onClick={onResetView}>
        重置视图
      </Button>
    </aside>
  );
}
