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
  activeKey?: string;
  defaultActiveKey?: string;
  tabPosition?: "top" | "left";
  destroyOnHidden?: boolean;
  onChange?: (activeKey: string) => void;
  className?: string;
};

export function P4WorkspaceTabs({
  items,
  activeKey,
  defaultActiveKey = items[0]?.key,
  tabPosition = "top",
  destroyOnHidden = true,
  onChange,
  className,
}: P4WorkspaceTabsProps) {
  return (
    <div id="xx-p4-workspace-nav" className={className}>
      <Tabs
        className={`xx-p4-workspace-tabs${tabPosition === "left" ? " xx-p4-workspace-tabs--left" : ""}`}
        activeKey={activeKey}
        defaultActiveKey={defaultActiveKey}
        destroyOnHidden={destroyOnHidden}
        onChange={onChange}
        tabPosition={tabPosition}
        items={items}
      />
    </div>
  );
}
