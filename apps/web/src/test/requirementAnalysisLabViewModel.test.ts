import { describe, expect, test } from "vitest";

import type { RequirementAnalysisSession } from "../lib/api";
import { buildRequirementAnalysisWorkingDocumentViewModel } from "../lib/requirementAnalysisLabViewModel";

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
});

function buildSessionWithCrossBlockRevisions(): RequirementAnalysisSession {
  return {
    session_id: "session-1",
    topic: "默认运算软件需求规格说明",
    status: "waiting_user",
    orchestrator_id: "xg-heuristic-orchestrator",
    provider_id: "mock",
    model: "mock-requirement-analysis-v1",
    template_id: "81433号",
    knowledge_package_id: "airspace-domain-demo",
    write_policy: "patch_suggestion_only",
    created_at: "2026-05-05T00:00:00Z",
    updated_at: "2026-05-05T00:00:00Z",
    orchestrator: null,
    stable_contract: {
      formal_document: true,
      output_label: "P2 -> P3 输出",
      description: "正式需求规格文档",
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
          apply_mode: "append_to_block",
          start_offset: 25,
          end_offset: 42,
          user_input_summary: "用户补充审查边界",
          supplement_reason: "补入审查目标",
          hit_spec_nodes: ["SPEC-REQ-1.1"],
          source_patch_ids: ["P-003"],
        },
      ],
    },
  };
}
