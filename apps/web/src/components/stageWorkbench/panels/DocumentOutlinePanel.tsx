import { Empty, Typography } from "antd";
import type { DocumentOutlineViewModel } from "../models";
import "../stage-document-workbench.css";

const { Text } = Typography;

type DocumentOutlinePanelProps = {
  outline: DocumentOutlineViewModel;
};

export function DocumentOutlinePanel({ outline }: DocumentOutlinePanelProps) {
  if (outline.sections.length === 0 && !outline.baseline) {
    return (
      <div className="stage-document-panel" data-testid="document-outline-panel">
        <Empty description={outline.emptyDescription} />
      </div>
    );
  }

  return (
    <div className="stage-document-tab-panel" data-testid="document-outline-panel">
      <div className="stage-document-rail-card">
        <h4>正文目录</h4>
        {outline.sections.length ? (
          <ol className="stage-document-list">
            {outline.sections.map((section) => (
              <li key={section.sectionId}>{section.title}</li>
            ))}
          </ol>
        ) : (
          <p>尚未生成软件设计说明正文。</p>
        )}
      </div>
      <div className="stage-document-rail-card">
        <h4>设计基线摘要</h4>
        {outline.baseline ? (
          <>
            <p>
              <Text strong>{outline.baseline.label}</Text>
            </p>
            <ul className="stage-document-list">
              <li>架构：{outline.baseline.architectureMode}</li>
              <li>模块：{outline.baseline.moduleCount} 个</li>
              <li>追溯：{outline.baseline.traceabilityCount} 条</li>
            </ul>
            <div className="stage-document-workorders">
              {outline.baseline.modules.map((module) => (
                <div className="stage-document-workorder" key={module.moduleId}>
                  {module.name}
                </div>
              ))}
            </div>
          </>
        ) : (
          <p>等待生成设计基线。</p>
        )}
      </div>
    </div>
  );
}
