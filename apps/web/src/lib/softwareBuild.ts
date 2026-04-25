import { api } from "./api";
import type {
  P5AssemblyAttempt,
  P5BuildOverview,
  P5DeliveryRuntimeClearResult,
  P5DeliveryOrder,
  P5DeliveryOrderDetail,
  P5DeliveryOrderSummary,
  P5DesignInputSource,
  P5FeedbackTask,
  P5InputBinding,
  P5SupplyInputSource,
  P5WorkspaceBootstrapResult,
} from "./api";

export type P5AttemptCreatePayload = {
  export_root: string;
  build_profile: string;
  attempt_note: string;
};

export type P5WorkspaceBootstrapPayload = {
  export_root: string;
  build_profile: string;
  attempt_note: string;
};

export type P5DeliveryOrderCreatePayload = {
  p3_order_id?: string | null;
  design_input_id?: string | null;
  requested_by: string;
  notes: string;
};

export type P5DesignInputSimPayload = {
  application_name: string;
  requirement_spec_id: string;
  baseline_id: string;
  notes: string;
  module_specs: ReadonlyArray<{
    module_id: string;
    name: string;
    objective: string;
    inputs: readonly string[];
    outputs: readonly string[];
    constraints: readonly string[];
    recommended_tools: readonly string[];
  }>;
};

export type P5SupplyInputSimPayload = {
  snapshot_name: string;
  notes: string;
  tools: ReadonlyArray<{
    tool_id: string;
    tool_name: string;
    tool_slug: string;
    verification_status: string;
    keywords: readonly string[];
  }>;
};

export type P5BindingConfirmPayload = {
  design_input_id: string;
  supply_input_id?: string | null;
  supply_mode: "snapshot" | "empty";
  confirmed_by: string;
};

export type P5ModuleBindingPayload = {
  tool_id: string;
  updated_by: string;
};

export type P5FeedbackReviewPayload = {
  decision: "confirmed" | "dismissed";
  reviewed_by: string;
  review_note: string;
};

export function getSoftwareBuildOverview() {
  return api.get<{ data: P5BuildOverview }>("/software-build/overview");
}

export function getSoftwareBuildOrders() {
  return api.get<{ data: { items: P5DeliveryOrderSummary[] } }>("/software-build/orders");
}

export function getSoftwareBuildOrderDetail(deliveryOrderId: string) {
  return api.get<P5DeliveryOrderDetail>(`/software-build/orders/${deliveryOrderId}`);
}

export function getSoftwareBuildDesignInputs() {
  return api.get<{ data: { items: P5DesignInputSource[] } }>("/software-build/design-inputs");
}

export function getSoftwareBuildSupplyInputs() {
  return api.get<{ data: { items: P5SupplyInputSource[] } }>("/software-build/supply-inputs");
}

export function createSoftwareBuildDesignInputSim(payload: P5DesignInputSimPayload) {
  return api.post<P5DesignInputSource>("/software-build/design-inputs/sim", payload);
}

export function createSoftwareBuildSupplyInputSim(payload: P5SupplyInputSimPayload) {
  return api.post<P5SupplyInputSource>("/software-build/supply-inputs/sim", payload);
}

export function createSoftwareBuildOrder(payload: P5DeliveryOrderCreatePayload) {
  return api.post<P5DeliveryOrder>("/software-build/orders", payload);
}

export function confirmSoftwareBuildBinding(deliveryOrderId: string, payload: P5BindingConfirmPayload) {
  return api.post<P5InputBinding>(`/software-build/orders/${deliveryOrderId}/binding/confirm`, payload);
}

export function updateSoftwareBuildModuleBinding(
  deliveryOrderId: string,
  moduleId: string,
  payload: P5ModuleBindingPayload,
) {
  return api.post<P5InputBinding>(`/software-build/orders/${deliveryOrderId}/module-bindings/${moduleId}`, payload);
}

export function createSoftwareBuildAttempt(deliveryOrderId: string, payload: P5AttemptCreatePayload) {
  return api.post<P5AssemblyAttempt>(`/software-build/orders/${deliveryOrderId}/attempts`, payload);
}

export function reviewSoftwareBuildFeedbackTask(
  deliveryOrderId: string,
  attemptId: string,
  taskId: string,
  payload: P5FeedbackReviewPayload,
) {
  return api.post<P5FeedbackTask>(
    `/software-build/orders/${deliveryOrderId}/attempts/${attemptId}/feedback-tasks/${taskId}/review`,
    payload,
  );
}

export function clearSoftwareBuildDeliveriesForTesting() {
  return api.post<P5DeliveryRuntimeClearResult>("/software-build/testing/clear-deliveries");
}

export function bootstrapSoftwareBuildWorkspace(payload: P5WorkspaceBootstrapPayload) {
  return api.post<P5WorkspaceBootstrapResult>("/software-build/workspace/bootstrap-demo", payload);
}
