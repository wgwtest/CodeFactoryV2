import type { ReactNode } from "react";
import "./stage-document-workbench.css";

type StageDocumentWorkbenchProps = {
  stage: string;
  className?: string;
  title: ReactNode;
  subtitle?: ReactNode;
  badges?: ReactNode;
  actions?: ReactNode;
  alert?: ReactNode;
  leftTop: ReactNode;
  leftBottom: ReactNode;
  main: ReactNode;
};

export function StageDocumentWorkbench({
  stage,
  className,
  title,
  subtitle,
  badges,
  actions,
  alert,
  leftTop,
  leftBottom,
  main,
}: StageDocumentWorkbenchProps) {
  return (
    <div className={["stage-document-workbench", className].filter(Boolean).join(" ")} data-stage={stage} data-testid="stage-document-workbench">
      <header className="stage-document-workbench-topbar">
        <div className="stage-document-workbench-heading">
          <div className="stage-document-workbench-title-row">
            {typeof title === "string" ? <h1 className="stage-document-workbench-title">{title}</h1> : title}
            {subtitle ? <span className="stage-document-workbench-subtitle">{subtitle}</span> : null}
          </div>
          {badges ? <div className="stage-document-workbench-badges">{badges}</div> : null}
        </div>
        {actions ? <div className="stage-document-workbench-actions">{actions}</div> : null}
      </header>
      {alert}
      <main className="stage-document-workbench-shell">
        <aside className="stage-document-workbench-left">
          {leftTop}
          {leftBottom}
        </aside>
        {main}
      </main>
    </div>
  );
}
