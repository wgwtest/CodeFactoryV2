import { describe, expect, test } from "vitest";

import type { RequirementAnalysisSession } from "../lib/api";
import {
  buildRequirementAnalysisWorkingDocumentViewModel,
  resolveDefaultRequirementAnalysisOrchestratorId,
  resolveDefaultRequirementAnalysisProviderId,
} from "../lib/requirementAnalysisLabViewModel";

describe("resolveDefaultRequirementAnalysisOrchestratorId", () => {
  test("uses the backend default plugin id when it is present", () => {
    const orchestratorId = resolveDefaultRequirementAnalysisOrchestratorId(
      [
        {
          orchestrator_id: "custom-plugin",
          plugin_id: "custom-plugin",
          name: "Custom Plugin",
          status: "active",
          description: "Custom plugin",
        },
      ],
      "custom-plugin",
    );

    expect(orchestratorId).toBe("custom-plugin");
  });

  test("falls back to the first discovered orchestrator instead of mapping legacy ids in the frontend", () => {
    const orchestratorId = resolveDefaultRequirementAnalysisOrchestratorId(
      [
        {
          orchestrator_id: "xg-local-heuristic-orchestrator",
          plugin_id: "xg-local-heuristic-orchestrator",
          name: "XG Heuristic Orchestrator",
          status: "active",
          description: "Discovered plugin",
        },
      ],
      "xg-strong-rule-orchestrator",
    );

    expect(orchestratorId).toBe("xg-local-heuristic-orchestrator");
  });
});

describe("resolveDefaultRequirementAnalysisProviderId", () => {
  test("does not lock the lab startup Provider before provider options are loaded", () => {
    expect(resolveDefaultRequirementAnalysisProviderId([], "mock")).toBe("");
  });

  test("prefers DeepSeek for the lab startup Provider when it is available", () => {
    const providerId = resolveDefaultRequirementAnalysisProviderId(
      [
        { provider_id: "mock", name: "Mock Provider", status: "active" },
        { provider_id: "deepseek", name: "DeepSeek", status: "active" },
      ],
      "mock",
    );

    expect(providerId).toBe("deepseek");
  });

  test("falls back to active mock provider when DeepSeek is not configured", () => {
    const providerId = resolveDefaultRequirementAnalysisProviderId(
      [
        { provider_id: "mock", name: "Mock Provider", status: "active" },
        { provider_id: "deepseek", name: "DeepSeek", status: "not_configured" },
      ],
      "deepseek",
    );

    expect(providerId).toBe("mock");
  });
});

describe("buildRequirementAnalysisWorkingDocumentViewModel", () => {
  test("groups right-side revision markers by turn and sorts them by first affected document position", () => {
    const session = buildSessionWithCrossBlockRevisions();

    const viewModel = buildRequirementAnalysisWorkingDocumentViewModel(session);

    expect(viewModel.revisionEvents).toHaveLength(2);
    expect(viewModel.revisionEvents.map((event) => event.turnId)).toEqual(["turn-0002", "turn-0001"]);
    expect(viewModel.revisionEvents[0]).toMatchObject({
      turnId: "turn-0002",
      colorToken: "turn-color-02",
      firstBlockId: "blk-0001",
      firstAnchorPath: "1 总则 / 编写目的",
      fragmentIds: ["frag-0003"],
      hitSpecNodes: ["SPEC-REQ-1.1"],
      deletedTexts: ["本规格说明用于定义通用分析软件。"],
    });
    expect(viewModel.revisionEvents[1]).toMatchObject({
      turnId: "turn-0001",
      colorToken: "turn-color-01",
      firstBlockId: "blk-0002",
      firstAnchorPath: "2 项目概述 / 软件定位",
      fragmentIds: ["frag-0001", "frag-0002"],
      hitSpecNodes: ["SPEC-REQ-2.1", "SPEC-REQ-3.1"],
    });
  });

  test("projects slash anchor paths into numbered document headings and sorts by document order", () => {
    const session = buildSessionWithCrossBlockRevisions();
    session.working_document.blocks = [
      {
        block_id: "blk-late-general",
        anchor_path: "1 总则 / 适用范围",
        block_type: "paragraph",
        order_index: 120,
        text: "本需求规格说明适用于态势分析系统第一阶段建设。",
        last_turn_id: "turn-0002",
        source_fragment_ids: [],
      },
      {
        block_id: "blk-product-scope",
        anchor_path: "2 总体描述 / 产品范围",
        block_type: "paragraph",
        order_index: 210,
        text: "系统第一阶段覆盖态势展示和地理信息分析。",
        last_turn_id: "turn-0001",
        source_fragment_ids: [],
      },
      {
        block_id: "blk-product-feature",
        anchor_path: "2 总体描述 / 产品功能",
        block_type: "paragraph",
        order_index: 220,
        text: "系统提供量算、坡度分析和部署分析工具。",
        last_turn_id: "turn-0001",
        source_fragment_ids: [],
      },
    ];

    const viewModel = buildRequirementAnalysisWorkingDocumentViewModel(session);

    expect(viewModel.blocks.map((block) => block.anchorPath)).toEqual([
      "1 总则 / 适用范围",
      "2 总体描述 / 产品范围",
      "2 总体描述 / 产品功能",
    ]);
    expect(viewModel.blocks.map((block) => block.displayHeading)).toEqual(["1.2 适用范围", "2.1 产品范围", "2.2 产品功能"]);
  });
});

function buildSessionWithCrossBlockRevisions(): RequirementAnalysisSession {
  return {
    session_id: "session-1",
    topic: "默认运算软件需求规格说明",
    status: "waiting_user",
    provider_id: "mock",
    model: "mock-requirement-analysis-v1",
    template_id: "81433号",
    knowledge_package_id: "airspace-domain-demo",
    write_policy: "patch_suggestion_only",
    created_at: "2026-05-05T00:00:00Z",
    updated_at: "2026-05-05T00:00:00Z",
    orchestrator: {
      orchestrator_id: "xg-heuristic-orchestrator",
      name: "XG Heuristic Orchestrator",
      status: "active",
      description: "需求分析组织器",
    },
    stable_contract: {
      formal_document: true,
      template_object: true,
      knowledge_binding: true,
      draft_persistence: true,
      check_and_freeze: true,
      p2_to_p3_output: true,
    },
    messages: [],
    confirmed_facts: [],
    open_questions: [],
    document_patch: [],
    questions: [],
    facts: [],
    patches: [],
    turns: [],
    provider_logs: [],
    annotations: [],
    risks: [],
    spec_tree: [],
    turn_path: [],
    active_spec_node_id: null,
    next_interaction: null,
    working_document: {
      document_id: "lab-working-document",
      title: "81433号需求规格说明（Lab 临时正文）",
      topic: "默认运算软件需求规格说明",
      template_id: "81433号",
      blocks: [
        {
          block_id: "blk-0001",
          anchor_path: "1 总则 / 编写目的",
          block_type: "paragraph",
          order_index: 10,
          text: "本规格说明用于定义运算软件首版的建设目标。后续补充面向专家审查的目标边界。",
          last_turn_id: "turn-0002",
          source_fragment_ids: ["frag-0002", "frag-0003"],
        },
        {
          block_id: "blk-0002",
          anchor_path: "2 项目概述 / 软件定位",
          block_type: "paragraph",
          order_index: 20,
          text: "本软件定位为通用运算分析工具。",
          last_turn_id: "turn-0001",
          source_fragment_ids: ["frag-0001"],
        },
        {
          block_id: "blk-0003",
          anchor_path: "3 功能需求 / 计算分析",
          block_type: "paragraph",
          order_index: 30,
          text: "系统提供基础计算分析能力。",
          last_turn_id: "turn-0001",
          source_fragment_ids: ["frag-0002"],
        },
      ],
      revision_fragments: [
        {
          fragment_id: "frag-0001",
          turn_id: "turn-0001",
          color_token: "turn-color-01",
          target_block_id: "blk-0002",
          apply_mode: "append_to_block",
          start_offset: 0,
          end_offset: 16,
          user_input_summary: "用户说明软件定位",
          supplement_reason: "补入软件定位",
          hit_spec_nodes: ["SPEC-REQ-2.1"],
          source_patch_ids: ["P-001"],
        },
        {
          fragment_id: "frag-0002",
          turn_id: "turn-0001",
          color_token: "turn-color-01",
          target_block_id: "blk-0003",
          apply_mode: "append_to_block",
          start_offset: 0,
          end_offset: 14,
          user_input_summary: "用户说明软件定位",
          supplement_reason: "补入计算分析能力",
          hit_spec_nodes: ["SPEC-REQ-3.1"],
          source_patch_ids: ["P-002"],
        },
        {
          fragment_id: "frag-0003",
          turn_id: "turn-0002",
          color_token: "turn-color-02",
          target_block_id: "blk-0001",
          apply_mode: "replace",
          start_offset: 0,
          end_offset: 42,
          deleted_text: "本规格说明用于定义通用分析软件。",
          user_input_summary: "用户补充审查边界",
          supplement_reason: "补入审查目标",
          hit_spec_nodes: ["SPEC-REQ-1.1"],
          source_patch_ids: ["P-003"],
        },
      ],
    },
  };
}
