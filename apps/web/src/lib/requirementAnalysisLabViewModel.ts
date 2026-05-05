import type {
  RequirementAnalysisFieldSchema,
  RequirementAnalysisLabConfig,
  RequirementAnalysisOrchestrator,
  RequirementAnalysisProvider,
  RequirementAnalysisSession,
  RequirementAnalysisTurn,
} from "./api";

export function resolveDefaultRequirementAnalysisOrchestratorId(
  orchestrators: RequirementAnalysisOrchestrator[],
  defaultOrchestratorId: string,
) {
  return (
    orchestrators.find((orchestrator) => orchestrator.orchestrator_id === defaultOrchestratorId)?.orchestrator_id ??
    orchestrators[0]?.orchestrator_id ??
    defaultOrchestratorId
  );
}

export function resolveDefaultRequirementAnalysisProviderId(providers: RequirementAnalysisProvider[], defaultProviderId: string) {
  return providers.find((provider) => provider.provider_id === defaultProviderId)?.provider_id ?? providers[0]?.provider_id ?? defaultProviderId;
}

export function resolveRequirementAnalysisWritePolicyLabel(
  policy: string,
  writePolicies: RequirementAnalysisLabConfig["write_policies"],
) {
  const configuredLabel = writePolicies.find((item) => item.policy_id === policy)?.label;
  if (configuredLabel) {
    return configuredLabel;
  }
  if (policy === "patch_suggestion_only") {
    return "只生成 document_patch 建议";
  }
  return policy;
}

export function getRequirementAnalysisProviderLogFieldNote(logSchema: RequirementAnalysisFieldSchema, path: string) {
  return logSchema.fields.find((field) => field.path === path)?.description ?? null;
}

export function buildRequirementAnalysisWorkingDocumentViewModel(session: RequirementAnalysisSession) {
  return {
    title: session.working_document.title,
    sections: session.working_document.sections.map((section) => ({
      sectionId: section.section_id,
      targetSection: section.target_section,
      content: section.content,
      sourcePatchIds: section.source_patch_ids,
      lastTurnId: section.last_turn_id,
      reviewStatus: section.review_status,
      reviewReason: section.review_reason,
    })),
  };
}

export function validateRequirementAnalysisTurnProtocol(turn: RequirementAnalysisTurn, requiredProperties: string[]): string[] {
  const value = turn as unknown as Record<string, unknown>;
  const missing: string[] = [];

  for (const property of requiredProperties) {
    if (!(property in value)) {
      missing.push(property);
    }
  }
  if (!isRecord(value.previous_interaction)) {
    missing.push("previous_interaction.prompt");
  }
  if (!isRecord(value.input_relation)) {
    missing.push("input_relation.relation");
    missing.push("input_relation.reason");
  }
  if (!isRecord(value.spec_execution)) {
    missing.push("spec_execution.interpretation");
    missing.push("spec_execution.document_patch");
    missing.push("spec_execution.working_document_update");
  }
  if (!isRecord(value.post_update_review)) {
    missing.push("post_update_review.summary");
    missing.push("post_update_review.section_review");
    missing.push("post_update_review.global_review");
  }
  if (!isRecord(value.closure_decision)) {
    missing.push("closure_decision.status");
    missing.push("closure_decision.reason");
  }
  if (!isRecord(value.next_interaction)) {
    missing.push("next_interaction.prompt");
  }
  if (!Array.isArray(value.decision_trace)) {
    missing.push("decision_trace");
  }

  return Array.from(new Set(missing));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
