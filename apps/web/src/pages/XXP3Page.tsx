import { startTransition, useEffect, useRef, useState } from "react";
import { Alert, Card, Col, Empty, Row, Space, Spin } from "antd";

import { P3DesignWorkspace } from "../components/p3/P3DesignWorkspace";
import { P3Hero } from "../components/p3/P3Hero";
import { P3OrderContextPanel } from "../components/p3/P3OrderContextPanel";
import { P3OrderQueue } from "../components/p3/P3OrderQueue";
import { P3ReviewWorkspace } from "../components/p3/P3ReviewWorkspace";
import { P3WorkorderBatchWorkspace } from "../components/p3/P3WorkorderBatchWorkspace";
import { P3WorkspaceTabs } from "../components/p3/P3WorkspaceTabs";
import type { P3OrderDetail, P3OrderSummary, P3WorkorderBatch, SoftwareDesignOverview } from "../lib/api";
import {
  approveSoftwareDesignOrder,
  createReviewThread,
  freezeSoftwareDesign,
  generateSoftwareDesignDraft,
  generateWorkorderBatch,
  getSoftwareDesignOrderDetail,
  getSoftwareDesignOrders,
  getSoftwareDesignOverview,
  pushWorkorderBatchToP4,
} from "../lib/softwareDesign";

export function XXP3Page() {
  const [overview, setOverview] = useState<SoftwareDesignOverview | null>(null);
  const [orders, setOrders] = useState<P3OrderSummary[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<P3OrderDetail | null>(null);
  const [workorderBatch, setWorkorderBatch] = useState<P3WorkorderBatch | null>(null);
  const [activeWorkspace, setActiveWorkspace] = useState("overview");
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

  async function loadOrderDetail(orderId: string, requestId = beginOrderRequest()) {
    const detailResponse = await getSoftwareDesignOrderDetail(orderId);
    if (requestId !== latestOrderRequestRef.current) {
      return;
    }
    const detail = normalizeOrderDetail(orderId, detailResponse.data);
    setSelectedOrder(detail);
    setWorkorderBatch(detail.workorder_batch);
  }

  async function loadPage(showLoading = false) {
    if (showLoading) {
      setLoading(true);
    }
    const requestId = beginOrderRequest();
    try {
      const [overviewResponse, ordersResponse] = await Promise.all([
        getSoftwareDesignOverview(),
        getSoftwareDesignOrders(),
      ]);
      const orderItems = ordersResponse.data.data.items;
      const initialOrderId = selectedOrderId ?? orderItems[0]?.order_id ?? null;
      const detailResponse = initialOrderId ? await getSoftwareDesignOrderDetail(initialOrderId) : null;
      if (requestId !== latestOrderRequestRef.current) {
        return;
      }
      const detail = detailResponse && initialOrderId ? normalizeOrderDetail(initialOrderId, detailResponse.data) : null;
      startTransition(() => {
        setOverview(overviewResponse.data.data);
        setOrders(orderItems);
        setSelectedOrderId(initialOrderId);
        setSelectedOrder(detail);
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
    const requestId = beginOrderRequest();
    const response = await generateWorkorderBatch(orderId);
    if (requestId !== latestOrderRequestRef.current) {
      return;
    }
    setWorkorderBatch(response.data);
    setSelectedOrder((currentOrder) =>
      currentOrder
        ? {
            ...currentOrder,
            order_id: currentOrder.order_id || orderId,
            workorder_batch: response.data,
          }
        : currentOrder,
    );
    return response.data;
  }

  async function handlePushToP4() {
    const orderId = selectedOrder?.order_id ?? selectedOrderId;
    if (!orderId) {
      return;
    }
    await pushWorkorderBatchToP4(orderId);
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
                }}
                onGenerateDraft={async (orderId) => {
                  const requestId = beginOrderRequest();
                  await generateSoftwareDesignDraft(orderId);
                  await loadOrderDetail(orderId, requestId);
                }}
              />
              <P3OrderContextPanel order={selectedOrder} />
            </Space>
          </Col>

          <Col xs={24} xl={16}>
            {selectedOrder ? (
              <Card style={{ borderRadius: 20, boxShadow: "0 18px 36px rgba(15, 23, 42, 0.08)" }}>
                <P3WorkspaceTabs
                  activeKey={activeWorkspace}
                  items={[
                    {
                      key: "overview",
                      label: "总览",
                      children: <P3OrderContextPanel order={selectedOrder} />,
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
                            const orderId = selectedOrder.order_id || selectedOrderId;
                            if (!orderId) {
                              return;
                            }
                            const requestId = beginOrderRequest();
                            await createReviewThread(orderId, payload);
                            await loadOrderDetail(orderId, requestId);
                          }}
                          onFreeze={async () => {
                            const orderId = selectedOrder.order_id || selectedOrderId;
                            if (!orderId) {
                              return;
                            }
                            await freezeSoftwareDesign(orderId);
                            setSelectedOrder((currentOrder) =>
                              currentOrder
                                ? {
                                    ...currentOrder,
                                    order_id: currentOrder.order_id || orderId,
                                    status: "frozen",
                                  }
                                : currentOrder,
                            );
                          }}
                        />
                      ),
                    },
                    {
                      key: "workorders",
                      label: "模块工单包",
                      children: (
                        <P3WorkorderBatchWorkspace
                          order={{
                            ...selectedOrder,
                            workorder_batch: workorderBatch ?? selectedOrder.workorder_batch,
                          }}
                          onGenerateBatch={handleGenerateBatch}
                          onPushToP4={handlePushToP4}
                        />
                      ),
                    },
                  ]}
                  onChange={setActiveWorkspace}
                />
              </Card>
            ) : (
              <Card style={{ borderRadius: 20 }}>
                <Empty description="当前没有可查看的订单" />
              </Card>
            )}
          </Col>
        </Row>
      </div>
    </div>
  );
}
