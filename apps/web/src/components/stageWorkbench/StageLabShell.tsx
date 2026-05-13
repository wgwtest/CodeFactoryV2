import type { ReactNode } from "react";
import { Tag, Typography } from "antd";
import "./stage-lab-shell.css";

const { Text, Title } = Typography;

export type StageLabNavigationItem = {
  key: string;
  title: string;
  subtitle: string;
  badge: string;
  disabled?: boolean;
};

type StageLabShellProps = {
  title: ReactNode;
  subtitle: ReactNode;
  mark?: string;
  badges?: ReactNode;
  actions?: ReactNode;
  alert?: ReactNode;
  navigationLabel: string;
  navigationItems: StageLabNavigationItem[];
  activeNavigationKey: string;
  onNavigationChange: (key: string) => void;
  workspace: ReactNode;
  className?: string;
  navigationTestId?: string;
  workspaceTestId?: string;
};

export function StageLabShell({
  title,
  subtitle,
  mark = "LAB",
  badges,
  actions,
  alert,
  navigationLabel,
  navigationItems,
  activeNavigationKey,
  onNavigationChange,
  workspace,
  className,
  navigationTestId,
  workspaceTestId,
}: StageLabShellProps) {
  return (
    <main className={["stage-lab-shell", className].filter(Boolean).join(" ")}>
      <header className="stage-lab-shell-topbar">
        <div className="stage-lab-shell-brand">
          <div className="stage-lab-shell-mark">{mark}</div>
          <div>
            {typeof title === "string" ? <Title level={2}>{title}</Title> : title}
            {typeof subtitle === "string" ? <Text type="secondary">{subtitle}</Text> : subtitle}
            {badges ? <div className="stage-lab-shell-badges">{badges}</div> : null}
          </div>
        </div>
        {actions ? <div className="stage-lab-shell-actions">{actions}</div> : null}
      </header>
      {alert}
      <section className="stage-lab-shell-layout">
        <aside
          aria-label={navigationLabel}
          className="stage-lab-shell-sidebar"
          data-testid={navigationTestId}
          role="tablist"
        >
          {navigationItems.map((item) => (
            <button
              aria-label={`${item.title} ${item.badge}`}
              aria-selected={activeNavigationKey === item.key}
              className={activeNavigationKey === item.key ? "stage-lab-shell-tab is-active" : "stage-lab-shell-tab"}
              disabled={item.disabled}
              key={item.key}
              onClick={() => onNavigationChange(item.key)}
              role="tab"
              type="button"
            >
              <span className="stage-lab-shell-tab-copy">
                <Text strong>{item.title}</Text>
                <Text type="secondary">{item.subtitle}</Text>
              </span>
              <Tag>{item.badge}</Tag>
            </button>
          ))}
        </aside>
        <section className="stage-lab-shell-workspace" data-testid={workspaceTestId}>
          {workspace}
        </section>
      </section>
    </main>
  );
}
