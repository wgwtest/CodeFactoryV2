import type {
  RequirementAuthoringDocumentDetail,
  RequirementAuthoringDocumentStatus,
  RequirementAuthoringWorkbenchConfig,
} from "./api";

export function formatRequirementAuthoringDocumentStatus(status: string): string {
  const labels: Record<string, string> = {
    draft: "草稿",
    checking: "检查中",
    ready_to_freeze: "待冻结",
    frozen: "已冻结",
    submitted_to_p3: "已提交 P3",
    archived: "已归档",
  };
  return labels[status] ?? status;
}

export function formatRequirementAuthoringDocumentStatusWithConfig(
  status: string,
  config: RequirementAuthoringWorkbenchConfig | null,
): string {
  return config?.document_statuses.find((item) => item.status === status)?.label ?? formatRequirementAuthoringDocumentStatus(status);
}

export function isRequirementAuthoringDocumentEditable(
  status: string,
  config: RequirementAuthoringWorkbenchConfig | null,
): boolean {
  return config?.document_statuses.find((item) => item.status === status)?.editable ?? status !== "frozen";
}

export function getRequirementAuthoringWorkbenchAction(config: RequirementAuthoringWorkbenchConfig | null, actionId: string) {
  return config?.actions.find((action) => action.action_id === actionId) ?? null;
}

export function getRequirementAuthoringWorkbenchActionLabel(
  config: RequirementAuthoringWorkbenchConfig | null,
  actionId: string,
  fallback: string,
): string {
  return getRequirementAuthoringWorkbenchAction(config, actionId)?.label ?? fallback;
}

export function isRequirementAuthoringActionDisabled({
  actionId,
  config,
  currentDocument,
  submitting,
  hasSelectedTemplate,
}: {
  actionId: string;
  config: RequirementAuthoringWorkbenchConfig | null;
  currentDocument: RequirementAuthoringDocumentDetail | null;
  submitting: boolean;
  hasSelectedTemplate: boolean;
}) {
  if (submitting) {
    return true;
  }
  if (actionId === "create_document") {
    return !hasSelectedTemplate || !config;
  }
  if (actionId === "open_document") {
    return false;
  }

  const action = getRequirementAuthoringWorkbenchAction(config, actionId);
  if (action?.requires_document && !currentDocument) {
    return true;
  }
  if (action?.disabled_when_frozen && currentDocument && !isRequirementAuthoringDocumentEditable(currentDocument.status, config)) {
    return true;
  }
  return false;
}

export function isKnownRequirementAuthoringDocumentStatus(status: string): status is RequirementAuthoringDocumentStatus {
  return ["draft", "checking", "ready_to_freeze", "frozen", "submitted_to_p3", "archived"].includes(status);
}
