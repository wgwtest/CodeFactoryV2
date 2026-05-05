import { startTransition, useEffect, useRef, useState } from "react";
import { Alert, Card, Col, Empty, Row, Space, Spin } from "antd";

import { P3DesignWorkspace } from "../components/p3/P3DesignWorkspace";
import { P3Hero } from "../components/p3/P3Hero";
import { P3OrderQueue } from "../components/p3/P3OrderQueue";
import { P3RequirementIntakePanel } from "../components/p3/P3RequirementIntakePanel";
import { P3ReviewWorkspace } from "../components/p3/P3ReviewWorkspace";
import { P3TemplateCenterWorkspace } from "../components/p3/P3TemplateCenterWorkspace";
import { P3WorkorderBatchWorkspace } from "../components/p3/P3WorkorderBatchWorkspace";
import { P3WorkspaceTabs } from "../components/p3/P3WorkspaceTabs";
import type {
  P3OrderDetail,
  P3OrderSummary,
  P3ReferenceCenter,
  P3StandardSearchResult,
  P3WorkorderBatch,
  RequirementSpecSummary,
  SoftwareDesignOverview,
} from "../lib/api";
import { getRequirementSpecs } from "../lib/requirements";
import {
  approveSoftwareDesignOrder,
  createSoftwareDesignOrder,
  createReviewThread,
  freezeSoftwareDesign,
  generateSoftwareDesignDraft,
  generateWorkorderBatch,
  getSoftwareDesignOrderDetail,
  getSoftwareDesignOrders,
  getSoftwareDesignOverview,
  getSoftwareDesignReferenceCenter,
  pushWorkorderBatchToP4,
  rejectSoftwareDesignOrder,
  searchSoftwareDesignStandards,
} from "../lib/softwareDesign";

export function XXP3Page() {
  const [overview, setOverview] = useState<SoftwareDesignOverview | null>(null);
  const [requirementSpecs, setRequirementSpecs] = useState<RequirementSpecSummary[]>([]);
  const [orders, setOrders] = useState<P3OrderSummary[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<P3OrderDetail | null>(null);
  const [referenceCenter, setReferenceCenter] = useState<P3ReferenceCenter | null>(null);
  const [standardSearchQuery, setStandardSearchQuery] = useState("design description");
  const [standardSearchResults, setStandardSearchResults] = useState<P3StandardSearchResult[]>([]);
  const [workorderBatch, setWorkorderBatch] = useState<P3WorkorderBatch | null>(null);
  const [activeWorkspace, setActiveWorkspace] = useState("reference");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const latestOrderRequestRef = useRef(0);

  function beginOrderRequest() {
    latestOrderRequestRef.current += 1;
    return latestOrderRequestRef.current;
  }

  function normalizeOrderDetail(orderId: string, detail: P3OrderDetail): P3OrderDetail {
    return {
      ...detail,
      order_id: detail.order_id || orderId,
    };
  }

  async function refreshPageForOrder(orderId: string) {
    await loadPage(false, orderId);
  }

  async function loadOrderDetail(orderId: string, requestId = beginOrderRequest()) {
    const detailResponse = await getSoftwareDesignOrderDetail(orderId);
    if (requestId !== latestOrderRequestRef.current) {
      return;
    }
    const detail = normalizeOrderDetail(orderId, detailResponse.data);
    setSelectedOrder(detail);
    setWorkorderBatch(detail.workorder_batch);
  }

  async function loadPage(showLoading = false, preferredOrderId: string | null = null) {
    if (showLoading) {
      setLoading(true);
    }
    const requestId = beginOrderRequest();
    try {
      const [overviewResponse, requirementsResponse, ordersResponse, referenceCenterResponse] = await Promise.all([
        getSoftwareDesignOverview(),
        getRequirementSpecs(),
        getSoftwareDesignOrders(),
        getSoftwareDesignReferenceCenter(),
      ]);
      const orderItems = ordersResponse.data.data.items;
      const initialOrderId = preferredOrderId ?? selectedOrderId ?? orderItems[0]?.order_id ?? null;
      const detailResponse = initialOrderId ? await getSoftwareDesignOrderDetail(initialOrderId) : null;
      if (requestId !== latestOrderRequestRef.current) {
        return;
      }
      const detail = detailResponse && initialOrderId ? normalizeOrderDetail(initialOrderId, detailResponse.data) : null;
      const center = referenceCenterResponse.data;
      startTransition(() => {
        setOverview(overviewResponse.data.data);
        setRequirementSpecs(requirementsResponse.data);
        setOrders(orderItems);
        setSelectedOrderId(initialOrderId);
        setSelectedOrder(detail);
        setReferenceCenter(center);
        setWorkorderBatch(detail?.workorder_batch ?? null);
        setError(null);
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载 XX-P3 数据失败");
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    void loadPage(true);
  }, []);

  async function handleGenerateBatch(): Promise<P3WorkorderBatch | void> {
    const orderId = selectedOrder?.order_id ?? selectedOrderId;
    if (!orderId) {
      return;
    }
    const response = await generateWorkorderBatch(orderId);
    await refreshPageForOrder(orderId);
    return response.data;
  }

  async function handlePushToP4() {
    const orderId = selectedOrder?.order_id ?? selectedOrderId;
    if (!orderId) {
      return;
    }
    await pushWorkorderBatchToP4(orderId);
    await refreshPageForOrder(orderId);
  }

  async function handleSearchStandards() {
    const response = await searchSoftwareDesignStandards(standardSearchQuery);
    setStandardSearchResults(response.data.items);
  }

  async function handleCreateOrder(specId: string) {
    const response = await createSoftwareDesignOrder({
      requirement_spec_id: specId,
      requested_by: "P3值班台",
      notes: "由 XX-P3 受理并进入软件设计编制流程。",
    });
    setSelectedOrderId(response.data.order_id);
    setActiveWorkspace("design");
    await loadPage(false, response.data.order_id);
  }

  if (loading && !overview) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!overview) {
    return (
      <div style={{ padding: 32 }}>
        <Alert type="error" showIcon message={error ?? "XX-P3 加载失败"} />
      </div>
    );
  }

  return (
    <div id="xx-p3-page" style={{ minHeight: "100vh", background: "#f6f8fa", padding: "24px 24px 32px" }}>
      <div style={{ maxWidth: 1440, margin: "0 auto 20px" }}>
        <Card
          style={{
            borderRadius: 20,
            border: "1px solid #d0d7de",
            background: "linear-gradient(135deg, #0f172a 0%, #1d4ed8 52%, #0f766e 100%)",
            boxShadow: "0 10px 24px rgba(31, 35, 40, 0.06)",
          }}
        >
          <P3Hero overview={overview} />
        </Card>
      </div>

      <div style={{ maxWidth: 1440, margin: "0 auto" }}>
        {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

        <Row gutter={[16, 16]}>
          <Col xs={24} xl={8}>
            <Space direction="vertical" size={16} style={{ display: "flex" }}>
              <P3RequirementIntakePanel
                specs={requirementSpecs}
                acceptedRequirementSpecIds={orders.map((order) => order.requirement_spec_id)}
                onCreateOrder={handleCreateOrder}
              />
              <P3OrderQueue
                orders={orders}
                selectedOrderId={selectedOrderId}
                onSelectOrder={async (orderId) => {
                  setSelectedOrderId(orderId);
                  const requestId = beginOrderRequest();
                  await loadOrderDetail(orderId, requestId);
                }}
                onApprove={async (orderId) => {
                  await approveSoftwareDesignOrder(orderId);
                  await refreshPageForOrder(orderId);
                }}
                onReject={async (orderId) => {
                  await rejectSoftwareDesignOrder(orderId);
                  await refreshPageForOrder(orderId);
                }}
                onGenerateDraft={async (orderId) => {
                  await generateSoftwareDesignDraft(orderId);
                  await refreshPageForOrder(orderId);
                }}
              />
            </Space>
          </Col>

          <Col xs={24} xl={16}>
            <Card style={{ borderRadius: 20, boxShadow: "0 18px 36px rgba(15, 23, 42, 0.08)" }}>
              <P3WorkspaceTabs
                activeKey={activeWorkspace}
                items={[
                  {
                    key: "reference",
                    label: "模板与规范",
                    children: (
                      <P3TemplateCenterWorkspace
                        referenceCenter={referenceCenter}
                        searchQuery={standardSearchQuery}
                        searchResults={standardSearchResults}
                        onSearchQueryChange={setStandardSearchQuery}
                        onSearch={handleSearchStandards}
                      />
                    ),
                  },
                  {
                    key: "design",
                    label: "设计编制",
                    children: <P3DesignWorkspace order={selectedOrder} />,
                  },
                  {
                    key: "review",
                    label: "评审协作",
                    children: (
                      <P3ReviewWorkspace
                        order={selectedOrder}
                        onCreateThread={async (payload) => {
                          const orderId = selectedOrder?.order_id || selectedOrderId;
                          if (!orderId) {
                            return;
                          }
                          await createReviewThread(orderId, payload);
                          await refreshPageForOrder(orderId);
                        }}
                        onFreeze={async () => {
                          const orderId = selectedOrder?.order_id || selectedOrderId;
                          if (!orderId) {
                            return;
                          }
                          await freezeSoftwareDesign(orderId);
                          await refreshPageForOrder(orderId);
                        }}
                      />
                    ),
                  },
                  {
                    key: "workorders",
                    label: "模块工单包",
                    children: (
                      <P3WorkorderBatchWorkspace
                        order={
                          selectedOrder
                            ? {
                                ...selectedOrder,
                                workorder_batch: workorderBatch ?? selectedOrder.workorder_batch,
                              }
                            : null
                        }
                        onGenerateBatch={handleGenerateBatch}
                        onPushToP4={handlePushToP4}
                      />
                    ),
                  },
                ]}
                onChange={setActiveWorkspace}
              />
              {!selectedOrder ? (
                <div style={{ marginTop: 12 }}>
                  <Empty description="当前没有可查看的订单" />
                </div>
              ) : null}
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  );
}
