import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api"
});

export type ArchiveReviewStatus = "pending" | "approved" | "rejected";

export type DocumentParseRun = {
  id: string;
  status: string;
  parser_name: string;
  parser_version?: string;
  failure_reason?: string | null;
  segment_count?: number;
  created_at?: string;
};

export type DocumentSegmentPreview = {
  id: string;
  block_type: string;
  heading: string;
  content: string;
  anchor: Record<string, string | number>;
};

export type DocumentVersionDetail = {
  id: string;
  version_number: number;
  file_name: string;
  mime_type: string;
  status: string;
  created_at: string;
  latest_parse_run: DocumentParseRun | null;
  parse_runs: DocumentParseRun[];
  segments_preview: DocumentSegmentPreview[];
};

export type IntakeDocumentSummary = {
  id: string;
  title: string;
  source_name: string;
  document_key: string;
  version_count: number;
  latest_version: DocumentVersionDetail | null;
};

export type IntakeDocumentDetail = {
  id: string;
  title: string;
  source_name: string;
  document_key: string;
  latest_version: DocumentVersionDetail | null;
  versions: DocumentVersionDetail[];
};

export type ArchiveKnowledgeSummary = {
  archive_id: string;
  document_count: number;
  entity_count: number;
  event_count: number;
  process_count: number;
};

export type ArchiveKnowledgeNode = {
  id: string;
  label: string;
  type: string;
  document_count: number;
};

export type ArchiveKnowledgeEdge = {
  source: string;
  target: string;
  label: string;
};

export type ArchiveKnowledgeGraph = {
  archive_id: string;
  nodes: ArchiveKnowledgeNode[];
  edges: ArchiveKnowledgeEdge[];
  summary: ArchiveKnowledgeSummary;
  publication?: ArchivePublicationVersion | null;
};

export type ArchiveKnowledgeInterpretation = {
  kind_label: string;
  family_code: string | null;
  family_label: string | null;
  display_name: string | null;
  standard_name: string | null;
  summary: string;
  producer_hint: string | null;
};

export type ArchiveKnowledgeEntity = {
  id: string;
  name: string;
  category: string;
  aliases: string[];
  document_count: number;
  interpretation: ArchiveKnowledgeInterpretation;
};

export type ArchiveKnowledgeEvidence = {
  document_id: string | null;
  document_title: string | null;
  excerpt: string;
};

export type ArchiveKnowledgeItemDetail = {
  id: string;
  name: string;
  item_type: string;
  category: string;
  aliases: string[];
  review_status: ArchiveReviewStatus;
  document_count: number;
  interpretation: ArchiveKnowledgeInterpretation;
  documents: Array<{
    id: string;
    title: string;
    file_type: string;
    source_archive: string;
  }>;
  evidence: ArchiveKnowledgeEvidence[];
  related_items: Array<{
    id: string;
    name: string;
    item_type: string;
    relation_type: string;
  }>;
};

export type ArchiveKnowledgeProcess = {
  id: string;
  name: string;
  category: string;
  document_ids: string[];
  evidence: Array<{ document_id: string; excerpt: string }>;
};

export type ArchiveKnowledgeDocument = {
  id: string;
  title: string;
  file_type: string;
  source_archive: string;
  character_count: number;
  entity_count: number;
  event_count: number;
  process_count: number;
  knowledge_item_count: number;
};

export type ArchiveKnowledgeDocumentKnowledgeItem = {
  id: string;
  name: string;
  item_type: string;
  category: string;
  aliases: string[];
  review_status: ArchiveReviewStatus;
  interpretation: ArchiveKnowledgeInterpretation;
  evidence: ArchiveKnowledgeEvidence[];
};

export type ArchiveKnowledgeDocumentDetail = {
  document: ArchiveKnowledgeDocument;
  knowledge_items: ArchiveKnowledgeDocumentKnowledgeItem[];
};

export type ArchiveReviewCandidate = {
  id: string;
  item_type: string;
  canonical_name: string;
  category: string;
  document_count: number;
  confidence: number;
  review_status: ArchiveReviewStatus;
  evidence_excerpt: string;
  evidence_document_title: string | null;
};

export type ArchiveKnowledgeItemUpdateInput = {
  name: string;
  category: string;
  aliases: string[];
};

export type ArchiveKnowledgeItemReviewInput = {
  review_status: ArchiveReviewStatus;
};

export type ArchiveKnowledgeBatchApproveInput = {
  item_ids: string[];
};

export type ArchiveKnowledgeMergeInput = {
  primary_item_id: string;
  secondary_item_id: string;
};

export type ArchivePublicationVersion = {
  version_label: string;
  publisher: string;
  published_at: string | null;
  summary: {
    document_count: number;
    entity_count: number;
    event_count: number;
    process_count: number;
  };
};

export type ArchivePublicationOverview = {
  archive_id: string;
  current_version: ArchivePublicationVersion | null;
  versions: ArchivePublicationVersion[];
  working_summary: {
    document_count: number;
    entity_count: number;
    event_count: number;
    process_count: number;
  };
};
