import type {
  ArchiveKnowledgeEdge,
  ArchiveKnowledgeEntity,
  ArchiveKnowledgeEvent,
  ArchiveKnowledgeItemDetail,
  ArchiveKnowledgeNode,
  ArchiveKnowledgeProcess,
} from "../../../../lib/api";

export type KnowledgeResultKind = "entity" | "event" | "process" | "graph_node";

export type KnowledgeGraphMode = "semantic_cluster" | "focus_neighborhood";

export type KnowledgeResultRow = {
  id: string;
  name: string;
  kind: KnowledgeResultKind;
  kindLabel: string;
  category: string;
  documentCount: number;
  summary: string;
  aliases: string[];
};

export type KnowledgeRelationRow = ArchiveKnowledgeEdge & {
  id: string;
};

export type KnowledgeResultsState = {
  entities: ArchiveKnowledgeEntity[];
  events: ArchiveKnowledgeEvent[];
  processes: ArchiveKnowledgeProcess[];
  graphNodes: ArchiveKnowledgeNode[];
  graphEdges: ArchiveKnowledgeEdge[];
  visibleGraphMode: KnowledgeGraphMode;
  selectedObjectId: string | null;
  selectedRelationId: string | null;
  selectedDetail: ArchiveKnowledgeItemDetail | null;
};
