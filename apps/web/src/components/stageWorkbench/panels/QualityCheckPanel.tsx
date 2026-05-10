import type { StageQualityGateViewModel } from "../models";
import "../stage-document-workbench.css";

type QualityCheckPanelProps = {
  quality: StageQualityGateViewModel;
};

export function QualityCheckPanel({ quality }: QualityCheckPanelProps) {
  return (
    <div className="stage-document-tab-panel" data-testid="quality-check-panel">
      <div className="stage-document-rail-card">
        <h4>设计完整性检查</h4>
        {quality.status === "not_run" ? (
          <>
            <p>{quality.emptyDescription}</p>
            <p>生成设计基线后，可检查正文、模块、接口、追溯和 P4 投影是否满足冻结准备条件。</p>
          </>
        ) : (
          <>
            <ul className="stage-document-list">
              <li>阻断项：{quality.summary.blockingCount}</li>
              <li>警告项：{quality.summary.warningCount}</li>
              <li>通过项：{quality.summary.passedCount}</li>
            </ul>
            {quality.gates.length ? (
              <div className="stage-document-gate-list">
                {quality.gates.map((gate) => (
                  <div className="stage-document-gate" key={gate.itemId}>
                    <strong>{gate.title}</strong>
                    <p>{gate.description}</p>
                  </div>
                ))}
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
