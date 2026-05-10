import type { ReactNode } from "react";
import { Tabs } from "antd";
import "./stage-document-workbench.css";

export type DocumentProductSurfaceTab = {
  key: string;
  label: string;
  children: ReactNode;
};

type DocumentProductSurfaceProps = {
  tabs: DocumentProductSurfaceTab[];
  defaultActiveKey?: string;
};

export function DocumentProductSurface({ tabs, defaultActiveKey }: DocumentProductSurfaceProps) {
  return (
    <div className="document-product-surface" data-testid="document-product-surface">
      <Tabs
        defaultActiveKey={defaultActiveKey ?? tabs[0]?.key}
        items={tabs.map((tab) => ({
          key: tab.key,
          label: tab.label,
          children: <div className="document-product-surface-pane">{tab.children}</div>,
        }))}
      />
    </div>
  );
}
