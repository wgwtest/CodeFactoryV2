import { api } from "./api";

export type WorkspaceLayoutRecord = {
  layout_id: string;
  owner_user_id: string;
  scope_type: string;
  scope_id: string;
  layout_kind: string;
  layout_role: string;
  name: string;
  is_default: boolean;
  payload_schema_version: string;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  last_used_at: string;
};

export type WorkspaceLayoutEnvelope = {
  items: WorkspaceLayoutRecord[];
};

export type WorkspaceLayoutListParams = {
  owner_user_id?: string;
  scope_type: string;
  scope_id: string;
  layout_kind: string;
  layout_role?: string;
};

export type WorkspaceLayoutCreateInput = {
  owner_user_id?: string;
  scope_type: string;
  scope_id: string;
  layout_kind: string;
  layout_role: string;
  name: string;
  is_default?: boolean;
  payload_schema_version: string;
  payload: Record<string, unknown>;
};

export type WorkspaceLayoutCurrentInput = {
  owner_user_id?: string;
  scope_type: string;
  scope_id: string;
  layout_kind: string;
  name: string;
  payload_schema_version: string;
  payload: Record<string, unknown>;
};

export async function listWorkspaceLayouts(params: WorkspaceLayoutListParams): Promise<WorkspaceLayoutEnvelope> {
  const response = await api.get<WorkspaceLayoutEnvelope>("/workspace-layouts", {
    params: {
      owner_user_id: params.owner_user_id ?? "default",
      scope_type: params.scope_type,
      scope_id: params.scope_id,
      layout_kind: params.layout_kind,
      ...(params.layout_role ? { layout_role: params.layout_role } : {}),
    },
  });
  return response.data;
}

export async function createWorkspaceLayout(payload: WorkspaceLayoutCreateInput): Promise<WorkspaceLayoutRecord> {
  const response = await api.post<WorkspaceLayoutRecord>("/workspace-layouts", {
    ...payload,
    owner_user_id: payload.owner_user_id ?? "default",
    is_default: payload.is_default ?? false,
  });
  return response.data;
}

export async function upsertCurrentWorkspaceLayout(payload: WorkspaceLayoutCurrentInput): Promise<WorkspaceLayoutRecord> {
  const response = await api.put<WorkspaceLayoutRecord>("/workspace-layouts/current", {
    ...payload,
    owner_user_id: payload.owner_user_id ?? "default",
  });
  return response.data;
}

export async function deleteWorkspaceLayout(layoutId: string): Promise<{ deleted_layout_id: string }> {
  const response = await api.delete<{ deleted_layout_id: string }>(`/workspace-layouts/${layoutId}`);
  return response.data;
}
