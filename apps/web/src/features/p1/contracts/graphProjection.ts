import type { P1StageStatus } from "./common";

export interface RuntimeGraphNode {
  node_id: string;
  label: string;
  node_type: "input_object" | "rule" | "action" | "output_object" | "quality_metric" | "publication" | "collection";
  stage_id: string;
  status: P1StageStatus;
  semantic_role: "input" | "basis" | "action" | "output" | "context";
  object_count?: number;
  payload_ref?: string;
}

export interface RuntimeGraphEdge {
  edge_id: string;
  source: string;
  target: string;
  relation: string;
  stage_id: string;
  evidence?: string;
}

export interface RuntimeGraphProjection {
  graph_projection_id: string;
  archive_id: string;
  document_id: string;
  view_mode: "semantic_aggregate" | "detail";
  layout_strategy: "layered_dag" | "force_assist" | "manual_adjusted";
  nodes: RuntimeGraphNode[];
  edges: RuntimeGraphEdge[];
  highlighted_node_ids: string[];
  highlighted_edge_ids: string[];
}
