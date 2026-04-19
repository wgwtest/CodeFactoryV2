import { api } from "./api";
import type {
  P5AssemblyAttempt,
  P5BuildOverview,
  P5DeliveryOrderDetail,
  P5DeliveryOrderSummary,
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

export function getSoftwareBuildOverview() {
  return api.get<{ data: P5BuildOverview }>("/software-build/overview");
}

export function getSoftwareBuildOrders() {
  return api.get<{ data: { items: P5DeliveryOrderSummary[] } }>("/software-build/orders");
}

export function getSoftwareBuildOrderDetail(deliveryOrderId: string) {
  return api.get<P5DeliveryOrderDetail>(`/software-build/orders/${deliveryOrderId}`);
}

export function createSoftwareBuildAttempt(deliveryOrderId: string, payload: P5AttemptCreatePayload) {
  return api.post<P5AssemblyAttempt>(`/software-build/orders/${deliveryOrderId}/attempts`, payload);
}

export function bootstrapSoftwareBuildWorkspace(payload: P5WorkspaceBootstrapPayload) {
  return api.post<P5WorkspaceBootstrapResult>("/software-build/workspace/bootstrap-demo", payload);
}
