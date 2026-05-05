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
  const fragmentsByBlock = new Map<string, RequirementAnalysisSession["working_document"]["revision_fragments"]>();
  const blocksById = new Map(session.working_document.blocks.map((block) => [block.block_id, block]));
  for (const fragment of session.working_document.revision_fragments) {
    const current = fragmentsByBlock.get(fragment.target_block_id) ?? [];
    current.push(fragment);
    fragmentsByBlock.set(fragment.target_block_id, current);
  }
  const blocks = [...session.working_document.blocks]
    .sort((left, right) => (left.order_index ?? 0) - (right.order_index ?? 0))
    .map((block) => ({
      blockId: block.block_id,
      anchorPath: block.anchor_path,
      blockType: block.block_type,
      text: block.text,
      lastTurnId: block.last_turn_id,
      sourceFragmentIds: block.source_fragment_ids,
      fragments: (fragmentsByBlock.get(block.block_id) ?? []).sort((left, right) => left.start_offset - right.start_offset),
    }));
  const blockOrderById = new Map(blocks.map((block, index) => [block.blockId, index]));
  const revisionEventsByTurn = new Map<
    string,
    {
      turnId: string;
      colorToken: string;
      firstBlockId: string;
      firstAnchorPath: string;
      firstPosition: number;
      fragmentIds: string[];
      summary: string;
      reason: string;
      hitSpecNodes: string[];
      deletedTexts: string[];
    }
  >();

  for (const fragment of session.working_document.revision_fragments) {
    const targetBlock = blocksById.get(fragment.target_block_id);
    const blockIndex = blockOrderById.get(fragment.target_block_id) ?? Number.MAX_SAFE_INTEGER;
    const firstPosition = blockIndex * 1_000_000 + fragment.start_offset;
    const current = revisionEventsByTurn.get(fragment.turn_id);
    const hitSpecNodes = appendUnique(current?.hitSpecNodes ?? [], fragment.hit_spec_nodes ?? []);
    const fragmentIds = [...(current?.fragmentIds ?? []), fragment.fragment_id];
    const deletedTexts = appendUnique(current?.deletedTexts ?? [], fragment.deleted_text ? [fragment.deleted_text] : []);

    if (!current || firstPosition < current.firstPosition) {
      revisionEventsByTurn.set(fragment.turn_id, {
        turnId: fragment.turn_id,
        colorToken: fragment.color_token,
        firstBlockId: fragment.target_block_id,
        firstAnchorPath: targetBlock?.anchor_path ?? "",
        firstPosition,
        fragmentIds,
        summary: fragment.user_input_summary ?? current?.summary ?? "",
        reason: fragment.supplement_reason ?? current?.reason ?? "",
        hitSpecNodes,
        deletedTexts,
      });
      continue;
    }

    revisionEventsByTurn.set(fragment.turn_id, {
      ...current,
      fragmentIds,
      hitSpecNodes,
      deletedTexts,
      summary: current.summary || fragment.user_input_summary || "",
      reason: current.reason || fragment.supplement_reason || "",
    });
  }
  const revisionEvents = [...revisionEventsByTurn.values()]
    .map((event) => ({
      ...event,
      fragmentIds: [...event.fragmentIds].sort((left, right) => {
        const leftFragment = session.working_document.revision_fragments.find((fragment) => fragment.fragment_id === left);
        const rightFragment = session.working_document.revision_fragments.find((fragment) => fragment.fragment_id === right);
        return fragmentDocumentPosition(leftFragment, blockOrderById) - fragmentDocumentPosition(rightFragment, blockOrderById);
      }),
    }))
    .sort((left, right) => left.firstPosition - right.firstPosition);

  return {
    title: session.working_document.title,
    topic: session.working_document.topic,
    blocks,
    revisionEvents,
    marginMarkers: session.working_document.revision_fragments.map((fragment) => ({
      fragmentId: fragment.fragment_id,
      turnId: fragment.turn_id,
      colorToken: fragment.color_token,
      targetBlockId: fragment.target_block_id,
      summary: fragment.user_input_summary ?? "",
      reason: fragment.supplement_reason ?? "",
      hitSpecNodes: fragment.hit_spec_nodes ?? [],
      deletedText: fragment.deleted_text ?? "",
    })),
  };
}

function appendUnique(current: string[], additions: string[]) {
  const result = [...current];
  for (const addition of additions) {
    if (addition && !result.includes(addition)) {
      result.push(addition);
    }
  }
  return result;
}

function fragmentDocumentPosition(
  fragment: RequirementAnalysisSession["working_document"]["revision_fragments"][number] | undefined,
  blockOrderById: Map<string, number>,
) {
  if (!fragment) {
    return Number.MAX_SAFE_INTEGER;
  }
  return (blockOrderById.get(fragment.target_block_id) ?? Number.MAX_SAFE_INTEGER) * 1_000_000 + fragment.start_offset;
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
    missing.push("post_update_review.target_review");
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
