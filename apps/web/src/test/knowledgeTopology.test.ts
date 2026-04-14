import { describe, expect, test } from "vitest";

import type { ArchiveKnowledgeEntity, ArchiveKnowledgeGraph } from "../lib/api";
import { buildVisibleGraph } from "../components/knowledgeTopology";

const graph: ArchiveKnowledgeGraph = {
  archive_id: "demo",
  nodes: [
    { id: "a", label: "国家空域系统", type: "system_or_service", item_type: "entity", document_count: 3 },
    { id: "b", label: "OV-1", type: "architecture_artifact", item_type: "entity", document_count: 2 },
    { id: "c", label: "孤立节点", type: "domain_concept", item_type: "entity", document_count: 1 },
  ],
  edges: [{ source: "a", target: "b", label: "describes" }],
  summary: {
    archive_id: "demo",
    document_count: 1,
    entity_count: 3,
    event_count: 0,
    process_count: 0,
  },
};

const entities: ArchiveKnowledgeEntity[] = [
  {
    id: "a",
    name: "国家空域系统",
    category: "system_or_service",
    aliases: ["NAS"],
    document_count: 3,
    interpretation: {
      kind_label: "系统/服务",
      family_code: null,
      family_label: null,
      display_name: null,
      standard_name: null,
      summary: "国家空域系统",
      producer_hint: null,
    },
  },
  {
    id: "b",
    name: "OV-1",
    category: "architecture_artifact",
    aliases: [],
    document_count: 2,
    interpretation: {
      kind_label: "架构工件",
      family_code: null,
      family_label: null,
      display_name: null,
      standard_name: null,
      summary: "OV-1",
      producer_hint: null,
    },
  },
  {
    id: "c",
    name: "孤立节点",
    category: "domain_concept",
    aliases: ["single"],
    document_count: 1,
    interpretation: {
      kind_label: "领域概念",
      family_code: null,
      family_label: null,
      display_name: null,
      standard_name: null,
      summary: "孤立节点",
      producer_hint: null,
    },
  },
];

describe("buildVisibleGraph", () => {
  test("hides isolated nodes in default topology view", () => {
    const aliasesById = new Map(entities.map((item) => [item.id, item.aliases]));
    const visible = buildVisibleGraph(graph, aliasesById, ["entity"], "");

    expect(visible.nodes.map((node) => node.id)).toEqual(["a", "b"]);
    expect(visible.edges).toHaveLength(1);
    expect(visible.hiddenIsolatedCount).toBe(1);
  });

  test("keeps isolated match visible when query hits it", () => {
    const aliasesById = new Map(entities.map((item) => [item.id, item.aliases]));
    const visible = buildVisibleGraph(graph, aliasesById, ["entity"], "single");

    expect(visible.nodes.map((node) => node.id)).toEqual(["c"]);
    expect(visible.edges).toHaveLength(0);
    expect(visible.hiddenIsolatedCount).toBe(0);
  });
});
