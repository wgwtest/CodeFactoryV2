import "./p3-workspace-tabs.css";

import { Tabs } from "antd";
import type { ReactNode } from "react";

type P3WorkspaceTab = {
  key: string;
  label: ReactNode;
  children: ReactNode;
};

type P3WorkspaceTabsProps = {
  activeKey: string;
  items: P3WorkspaceTab[];
  onChange: (activeKey: string) => void;
};

export function P3WorkspaceTabs({ activeKey, items, onChange }: P3WorkspaceTabsProps) {
  return (
    <div id="xx-p3-workspace-nav">
      <Tabs
        activeKey={activeKey}
        className="xx-p3-workspace-tabs"
        destroyOnHidden
        items={items}
        onChange={onChange}
        style={{ marginTop: 12 }}
      />
    </div>
  );
}
