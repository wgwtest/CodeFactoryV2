import { useEffect, useState } from "react";
import { Alert, Button, Card, Col, Empty, Input, List, Row, Space, Tag, Typography } from "antd";

import type { ToolDemandReviewDecisionInput, ToolDemandSheet } from "../../lib/api";
import { P4DemandItemBoard } from "./P4DemandItemBoard";
import { P4DemandSheetTree } from "./P4DemandSheetTree";
import { P4SupplyResultPreview } from "./P4SupplyResultPreview";

type P4InputChainWorkspaceProps = {
  sheets: ToolDemandSheet[];
  activeSheet: ToolDemandSheet | null;
  selectedItemId: string | null;
  refreshingItemId: string | null;
  reviewingItemId: string | null;
  rejectingCurrentSheet: boolean;
  clearingDemandSheets: boolean;
  error: string | null;
  onSelectSheet: (sheetId: string) => Promise<void>;
  onSelectItem: (itemId: string) => void;
  onRefreshProgress: (itemId: string) => Promise<void>;
  onReviewItem: (itemId: string, payload: ToolDemandReviewDecisionInput) => Promise<void>;
  onRejectCurrentSheet: () => Promise<void>;
  onClearDemandSheets: () => Promise<void>;
};

function renderLifecycleTag(status: string) {
  if (status === "accepted" || status === "submitted") {
    return <Tag color="blue">{status}</Tag>;
  }
  if (status === "withdrawn") {
    return <Tag color="orange">{status}</Tag>;
  }
  if (status === "rejected") {
    return <Tag color="red">{status}</Tag>;
  }
  if (status === "closed") {
    return <Tag>{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

function renderReviewTag(status: string) {
  if (status === "reviewed") {
    return <Tag color="green">{status}</Tag>;
  }
  if (status === "reviewing") {
    return <Tag color="blue">{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

function renderDeliveryTag(status: string) {
  if (status === "delivered") {
    return <Tag color="green">{status}</Tag>;
  }
  if (status === "delivering") {
    return <Tag color="blue">{status}</Tag>;
  }
  return <Tag color="gold">{status}</Tag>;
}

export function P4InputChainWorkspace({
  sheets,
  activeSheet,
  selectedItemId,
  refreshingItemId,
  reviewingItemId,
  rejectingCurrentSheet,
  clearingDemandSheets,
  error,
  onSelectSheet,
  onSelectItem,
  onRefreshProgress,
  onReviewItem,
  onRejectCurrentSheet,
  onClearDemandSheets,
}: P4InputChainWorkspaceProps) {
  const activeItem = activeSheet?.items?.find((item) => item.item_id === selectedItemId) ?? null;
  const [importanceScore, setImportanceScore] = useState("3");
  const [urgencyScore, setUrgencyScore] = useState("3");
  const [rationalityVerdict, setRationalityVerdict] = useState("合理");
  const [reviewComment, setReviewComment] = useState("");

  useEffect(() => {
    if (!activeItem) {
      return;
    }
    setImportanceScore(String(activeItem.importance_score ?? 3));
    setUrgencyScore(String(activeItem.urgency_score ?? 3));
    setRationalityVerdict(activeItem.rationality_verdict || "合理");
    setReviewComment(activeItem.review_comment || "");
  }, [activeItem?.item_id]);

  async function submitReview(decision: ToolDemandReviewDecisionInput["decision"]) {
    if (!activeItem) {
      return;
    }
    await onReviewItem(activeItem.item_id, {
      decision,
      importance_score: importanceScore ? Number(importanceScore) : null,
      urgency_score: urgencyScore ? Number(urgencyScore) : null,
      rationality_verdict: rationalityVerdict,
      review_comment: reviewComment,
      reviewed_by: "p4-reviewer",
    });
  }

  return (
    <div id="xx-p4-input-chain-workspace" className="xx-p4-pane-stack">
      {error ? <Alert id="xx-p4-input-chain-error" type="error" showIcon message={error} /> : null}

      <Card id="xx-p4-demand-sheet-intake-card" title="工序单受理区" className="xx-p4-panel-card">
        <Space direction="vertical" size={16} style={{ display: "flex" }}>
          <Typography.Paragraph style={{ margin: 0, color: "#475569" }}>
            P4 只受理已经提交的工具需求单，不在当前页内发起 P3 模拟发生，也不承载 P5 模拟消费。
          </Typography.Paragraph>
          <Typography.Paragraph style={{ margin: 0, color: "#475569" }}>新建总单请前往 /xx-p3-sim</Typography.Paragraph>
          <Typography.Paragraph style={{ margin: 0, color: "#475569" }}>
            结果消费与进度决策请前往 /xx-p5-sim
          </Typography.Paragraph>
          <Typography.Paragraph id="xx-p4-testing-clear-note" style={{ margin: 0, color: "#8b949e" }}>
            `测试一键清理全部工单` 仅用于当前联调闭环，会同时清空 P3 生成与 P4 受理的共享工单数据。
          </Typography.Paragraph>

          <Space id="xx-p4-demand-sheet-actions" wrap>
            <Button
              id="xx-p4-clear-all-demand-sheets-button"
              danger
              ghost
              loading={clearingDemandSheets}
              onClick={() => void onClearDemandSheets()}
            >
              测试一键清理全部工单
            </Button>
            {activeSheet &&
            activeSheet.lifecycle_status !== "withdrawn" &&
            activeSheet.lifecycle_status !== "rejected" ? (
              <Button
                id="xx-p4-reject-current-sheet-button"
                danger
                loading={rejectingCurrentSheet}
                onClick={() => void onRejectCurrentSheet()}
              >
                驳回当前工单
              </Button>
            ) : null}
          </Space>

          <div id="xx-p4-demand-sheet-list">
            {sheets.length === 0 ? (
              <Empty description="当前没有工具需求单" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <List
                size="small"
                dataSource={sheets}
                renderItem={(sheet) => {
                  const selected = sheet.sheet_id === activeSheet?.sheet_id;
                  return (
                    <List.Item key={sheet.sheet_id}>
                      <Space
                        align="center"
                        style={{ display: "flex", justifyContent: "space-between", width: "100%" }}
                        wrap
                      >
                        <Space direction="vertical" size={2} style={{ display: "flex" }}>
                          <Typography.Text strong>{`工单：${sheet.sheet_name}`}</Typography.Text>
                          <Typography.Text type="secondary">{`工单 ID：${sheet.sheet_id}`}</Typography.Text>
                        </Space>
                        <Space align="center" wrap>
                          {renderLifecycleTag(sheet.lifecycle_status)}
                          {renderReviewTag(sheet.review_status)}
                          {renderDeliveryTag(sheet.delivery_status)}
                          <Button
                            id={`xx-p4-view-sheet-${sheet.sheet_id}`}
                            type={selected ? "primary" : "default"}
                            onClick={() => void onSelectSheet(sheet.sheet_id)}
                          >
                            查看工单 {sheet.sheet_id}
                          </Button>
                        </Space>
                      </Space>
                    </List.Item>
                  );
                }}
              />
            )}
          </div>

          {activeSheet ? (
            <Space id="xx-p4-active-sheet-status-strip" wrap>
              <Typography.Text strong>{activeSheet.sheet_name}</Typography.Text>
              {renderLifecycleTag(activeSheet.lifecycle_status)}
              {renderReviewTag(activeSheet.review_status)}
              {renderDeliveryTag(activeSheet.delivery_status)}
              <Tag color="gold">待审 {activeSheet.pending_review_count}</Tag>
              <Tag color="green">直接交付 {activeSheet.approved_delivery_count}</Tag>
              <Tag color="blue">进入研制 {activeSheet.approved_manufacture_count}</Tag>
            </Space>
          ) : null}
        </Space>
      </Card>

      <Row id="xx-p4-input-chain-grid" className="xx-p4-input-chain-grid" gutter={[20, 20]}>
        <Col xs={24} xl={10}>
          <Card id="xx-p4-demand-item-board-card" title="工具需求列表" className="xx-p4-panel-card" style={{ height: "100%" }}>
            <P4DemandItemBoard
              items={activeSheet?.items ?? []}
              selectedItemId={selectedItemId}
              refreshingItemId={refreshingItemId}
              onSelectItem={onSelectItem}
              onRefreshProgress={onRefreshProgress}
            />
          </Card>
        </Col>

        <Col xs={24} xl={14}>
          <Card id="xx-p4-review-panel-card" title="需求审批与处置面板" className="xx-p4-panel-card" style={{ height: "100%" }}>
            {activeItem ? (
              <Space id="xx-p4-review-panel" direction="vertical" size={16} style={{ display: "flex" }}>
                <Card id="xx-p4-review-summary" size="small" title="需求摘要" className="xx-p4-subcard">
                  <Space direction="vertical" size={8} style={{ display: "flex" }}>
                    <Space wrap>
                      <Typography.Text strong>{activeItem.component_name}</Typography.Text>
                      <Tag color="cyan">{activeItem.recommendation_type}</Tag>
                      <Tag color="gold">{activeItem.review_status}</Tag>
                    </Space>
                    <Typography.Text>{activeItem.recommendation_summary}</Typography.Text>
                    <Typography.Text type="secondary">{activeItem.ancestry.join(" / ")}</Typography.Text>
                  </Space>
                </Card>

                <Card id="xx-p4-review-decision" size="small" title="审批决策" className="xx-p4-subcard">
                  <Space direction="vertical" size={12} style={{ display: "flex" }}>
                    <label htmlFor="xx-p4-importance-score">
                      <Typography.Text>重要性评分</Typography.Text>
                    </label>
                    <Input
                      id="xx-p4-importance-score"
                      aria-label="重要性评分"
                      type="number"
                      min={1}
                      max={5}
                      value={importanceScore}
                      onChange={(event) => setImportanceScore(event.target.value)}
                    />

                    <label htmlFor="xx-p4-urgency-score">
                      <Typography.Text>紧急性评分</Typography.Text>
                    </label>
                    <Input
                      id="xx-p4-urgency-score"
                      aria-label="紧急性评分"
                      type="number"
                      min={1}
                      max={5}
                      value={urgencyScore}
                      onChange={(event) => setUrgencyScore(event.target.value)}
                    />

                    <label htmlFor="xx-p4-rationality-verdict">
                      <Typography.Text>合理性判断</Typography.Text>
                    </label>
                    <Input
                      id="xx-p4-rationality-verdict"
                      aria-label="合理性判断"
                      value={rationalityVerdict}
                      onChange={(event) => setRationalityVerdict(event.target.value)}
                    />

                    <label htmlFor="xx-p4-review-comment">
                      <Typography.Text>审定备注</Typography.Text>
                    </label>
                    <Input.TextArea
                      id="xx-p4-review-comment"
                      aria-label="审定备注"
                      rows={3}
                      value={reviewComment}
                      onChange={(event) => setReviewComment(event.target.value)}
                    />

                    <Space wrap>
                      <Button
                        type="primary"
                        loading={reviewingItemId === activeItem.item_id}
                        disabled={activeItem.review_status !== "pending_review" || activeItem.recommendation_type !== "existing_tool"}
                        onClick={() => void submitReview("approve_delivery")}
                      >
                        批准并直接交付
                      </Button>
                      <Button
                        type="primary"
                        ghost
                        loading={reviewingItemId === activeItem.item_id}
                        disabled={
                          activeItem.review_status !== "pending_review" ||
                          activeItem.recommendation_type !== "manufacture_candidate"
                        }
                        onClick={() => void submitReview("approve_manufacture")}
                      >
                        批准并进入研制
                      </Button>
                      <Button
                        danger
                        loading={reviewingItemId === activeItem.item_id}
                        disabled={activeItem.review_status !== "pending_review"}
                        onClick={() => void submitReview("reject")}
                      >
                        驳回需求项
                      </Button>
                    </Space>
                  </Space>
                </Card>

                <Card id="xx-p4-review-supply-card" size="small" title="供给与交付结果" className="xx-p4-subcard">
                  <P4SupplyResultPreview item={activeItem} />
                </Card>

                <Card id="xx-p4-review-source-card" size="small" title="辅助来源信息" className="xx-p4-subcard">
                  <P4DemandSheetTree sheet={activeSheet} selectedItemId={selectedItemId} onSelectItem={onSelectItem} />
                </Card>
              </Space>
            ) : (
              <Empty description="请选择一个需求项开始审批与处置" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
