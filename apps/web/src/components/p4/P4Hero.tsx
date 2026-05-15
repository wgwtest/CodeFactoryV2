export function P4Hero() {
  return (
    <header id="xx-p4-hero" className="xx-p4-page-header">
      <div className="xx-p4-page-brand">
        <div className="xx-p4-page-mark" aria-hidden="true">
          P4
        </div>
        <div>
          <h1 id="xx-p4-hero-title" className="xx-p4-page-title">
            P4 工具仓库工作台
          </h1>
          <p id="xx-p4-hero-description" className="xx-p4-page-description">
            承接 P3 工具需求工单，完成工具匹配、构建、资产登记与演进巡检。
          </p>
        </div>
      </div>
      <div className="xx-p4-page-top-actions" aria-label="P4 工作台对齐状态">
        <span className="xx-p4-state-pill xx-p4-state-pill--navy">P3 工单接入</span>
        <span className="xx-p4-state-pill xx-p4-state-pill--teal">工具资产供给</span>
      </div>
    </header>
  );
}
