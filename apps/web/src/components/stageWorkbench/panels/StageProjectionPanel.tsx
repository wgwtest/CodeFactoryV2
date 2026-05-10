import type { StageOutputProjectionViewModel } from "../models";
import "../stage-document-workbench.css";

type StageProjectionPanelProps = {
  projection: StageOutputProjectionViewModel;
  note?: string;
};

export function StageProjectionPanel({ projection, note }: StageProjectionPanelProps) {
  return (
    <div className="stage-document-tab-panel" data-testid="stage-projection-panel">
      <div className="stage-document-rail-card">
        <h4>{projection.packageName}</h4>
        {projection.items.length ? (
          <div className="stage-document-workorders">
            {projection.items.map((item) => (
              <div className="stage-document-workorder" key={item.itemId}>
                {item.title}
              </div>
            ))}
          </div>
        ) : (
          <p>{projection.emptyDescription}</p>
        )}
      </div>
      {note ? (
        <div className="stage-document-rail-card">
          <h4>不兼容提示</h4>
          <p>{note}</p>
        </div>
      ) : null}
    </div>
  );
}
