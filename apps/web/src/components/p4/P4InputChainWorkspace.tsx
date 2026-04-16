import { Alert, Button, Card, Col, Row, Select, Space, Tag, Typography } from "antd";

import type { ToolDemandSheet } from "../../lib/api";
import { P4DemandItemBoard } from "./P4DemandItemBoard";
import { P4DemandSheetTree } from "./P4DemandSheetTree";
import { P4SupplyResultPreview } from "./P4SupplyResultPreview";

type P4InputChainWorkspaceProps = {
  sheets: ToolDemandSheet[];
  activeSheet: ToolDemandSheet | null;
  selectedItemId: string | null;
  creatingMockSheet: boolean;
  refreshingItemId: string | null;
  error: string | null;
  onGenerateMockSheet: () => Promise<void>;
  onSelectSheet: (sheetId: string) => Promise<void>;
  onSelectItem: (itemId: string) => void;
  onRefreshProgress: (itemId: string) => Promise<void>;
};

function renderStatusTag(status: string) {
  if (status === "ready") {
    return <Tag color="green">{status}</Tag>;
  }
  if (status === "processing" || status === "partially_ready") {
    return <Tag color="blue">{status}</Tag>;
  }
  if (status === "failed") {
    return <Tag color="red">{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

export function P4InputChainWorkspace({
  sheets,
  activeSheet,
  selectedItemId,
  creatingMockSheet,
  refreshingItemId,
  error,
  onGenerateMockSheet,
  onSelectSheet,
  onSelectItem,
  onRefreshProgress,
}: P4InputChainWorkspaceProps) {
  const activeItem = activeSheet?.items?.find((item) => item.item_id === selectedItemId) ?? null;

  return (
    <Space id="xx-p4-input-chain-workspace" direction="vertical" size={16} style={{ display: "flex" }}>
      {error ? <Alert id="xx-p4-input-chain-error" type="error" showIcon message={error} /> : null}

      <Card id="xx-p4-input-chain-generator-card" title="P3 模拟发生区" style={{ borderRadius: 18 }}>
        <Space direction="vertical" size={16} style={{ display: "flex" }}>
          <Typography.Paragraph style={{ margin: 0, color: "#475569" }}>
            当前页内置一个最小 P3 模拟入口，方便直接拉起 `模拟蓝军` 工具需求总单并进入 P4 处理闭环。
          </Typography.Paragraph>

          <Space wrap>
            <Button
              id="xx-p4-generate-mock-sheet"
              type="primary"
              loading={creatingMockSheet}
              onClick={() => void onGenerateMockSheet()}
            >
              生成模拟蓝军需求总单
            </Button>

            <Select
              id="xx-p4-active-sheet-select"
              aria-label="当前工具需求单"
              style={{ minWidth: 280 }}
              placeholder="选择已有需求单"
              value={activeSheet?.sheet_id}
              options={sheets.map((sheet) => ({
                label: `${sheet.sheet_name} · ${sheet.sheet_id}`,
                value: sheet.sheet_id,
              }))}
              onChange={(value) => void onSelectSheet(value)}
            />
          </Space>

          {activeSheet ? (
            <Space wrap>
              <Typography.Text strong>{activeSheet.sheet_name}</Typography.Text>
              {renderStatusTag(activeSheet.status)}
              <Tag color="cyan">叶子项 {activeSheet.item_count}</Tag>
              <Tag color="green">可取 {activeSheet.ready_for_fetch_count}</Tag>
              <Tag color="blue">制造中 {activeSheet.manufacturing_count}</Tag>
            </Space>
          ) : null}
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={10}>
          <Card id="xx-p4-demand-sheet-tree-card" title="总单树审查区" style={{ borderRadius: 18, height: "100%" }}>
            <P4DemandSheetTree sheet={activeSheet} selectedItemId={selectedItemId} onSelectItem={onSelectItem} />
          </Card>
        </Col>

        <Col xs={24} xl={14}>
          <Card id="xx-p4-demand-item-board-card" title="叶子项处理流水区" style={{ borderRadius: 18, height: "100%" }}>
            <P4DemandItemBoard
              items={activeSheet?.items ?? []}
              selectedItemId={selectedItemId}
              refreshingItemId={refreshingItemId}
              onSelectItem={onSelectItem}
              onRefreshProgress={onRefreshProgress}
            />
          </Card>
        </Col>
      </Row>

      <Card id="xx-p4-supply-preview-card" title="P5 输出预览区" style={{ borderRadius: 18 }}>
        <P4SupplyResultPreview item={activeItem} />
      </Card>
    </Space>
  );
}
