import "./p4-workspace-tabs.css";

import { Tabs } from "antd";
import type { ReactNode } from "react";

type P4WorkspaceTab = {
  key: string;
  label: ReactNode;
  children: ReactNode;
};

type P4WorkspaceTabsProps = {
  items: P4WorkspaceTab[];
};

export function P4WorkspaceTabs({ items }: P4WorkspaceTabsProps) {
  return (
    <div id="xx-p4-workspace-nav">
      <Tabs
        className="xx-p4-workspace-tabs"
        defaultActiveKey="overview"
        destroyOnHidden
        items={items}
      />
    </div>
  );
}
