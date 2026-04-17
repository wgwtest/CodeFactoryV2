import { api } from "./api";
import type {
  P3OrderDetail,
  P3OrderSummary,
  P3ReferenceCenter,
  P3StandardSearchResult,
  P3WorkorderBatch,
  SoftwareDesignOverview,
} from "./api";

export function getSoftwareDesignOverview() {
  return api.get<{ data: SoftwareDesignOverview }>("/software-design/overview");
}

export function getSoftwareDesignReferenceCenter() {
  return api.get<P3ReferenceCenter>("/software-design/reference-center");
}

export function searchSoftwareDesignStandards(query: string) {
  return api.get<{ items: P3StandardSearchResult[] }>("/software-design/standards/search", {
    params: { q: query },
  });
}

export function getSoftwareDesignOrders() {
  return api.get<{ data: { items: P3OrderSummary[] } }>("/software-design/orders");
}

export function createSoftwareDesignOrder(payload: {
  requirement_spec_id: string;
  requested_by: string;
  notes: string;
}) {
  return api.post<{ order_id: string; status: string }>("/software-design/orders", payload);
}

export function getSoftwareDesignOrderDetail(orderId: string) {
  return api.get<P3OrderDetail>(`/software-design/orders/${orderId}`);
}

export function approveSoftwareDesignOrder(orderId: string) {
  return api.post<{ status: string }>(`/software-design/orders/${orderId}/approve`);
}

export function rejectSoftwareDesignOrder(orderId: string) {
  return api.post<{ status: string }>(`/software-design/orders/${orderId}/reject`);
}

export function generateSoftwareDesignDraft(orderId: string) {
  return api.post<{ status: string }>(`/software-design/orders/${orderId}/generate-draft`);
}

export function createReviewThread(
  orderId: string,
  payload: { topic: string; anchor: string; message: string },
) {
  return api.post(`/software-design/orders/${orderId}/review-threads`, payload);
}

export function freezeSoftwareDesign(orderId: string) {
  return api.post<{ status: string }>(`/software-design/orders/${orderId}/freeze`);
}

export function generateWorkorderBatch(orderId: string) {
  return api.post<P3WorkorderBatch>(`/software-design/orders/${orderId}/workorder-batch`);
}

export function pushWorkorderBatchToP4(orderId: string) {
  return api.post<{ push_status: string }>(`/software-design/orders/${orderId}/push-to-p4`);
}
