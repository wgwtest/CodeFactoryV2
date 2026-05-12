import type { TagProps } from "antd";

export type IntakeParseStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export type IntakeAvailability = "available" | "warning" | "unavailable";

export type IntakeContractDocument = {
  document_id: string;
  title: string;
  file_name: string;
  file_type: string;
  source_path: string;
  parse_status: IntakeParseStatus;
  parse_error: string | null;
  segment_count: number;
  anchor_count: number;
  can_enter_runtime: boolean;
};

export type IntakeContractSummary = {
  document_count: number;
  parsed_completed_count: number;
  parsed_failed_count: number;
  pending_count: number;
  can_enter_runtime_count: number;
  blocked_count: number;
};

export type IntakeContractSnapshot = {
  archive_id: string;
  document_set_id: string;
  source_dir: string;
  policy_package_version_id: string | null;
  documents: IntakeContractDocument[];
  summary: IntakeContractSummary;
  preflight_issues: string[];
};

export type IntakeContractEnvelope = {
  contract_version: string;
  source_kind: "live" | "fixture" | "mock_fallback";
  generated_at: string;
  data: IntakeContractSnapshot;
  warnings: string[];
};

export type IntakeDocumentRow = {
  id: string;
  documentId: string;
  title: string;
  fileName: string;
  fileType: string;
  sourcePath: string;
  parseStatus: IntakeParseStatus;
  parseStatusLabel: string;
  parseStatusColor: TagProps["color"];
  parseError: string | null;
  segmentCount: number;
  anchorCount: number;
  canEnterRuntime: boolean;
  runtimeStatus: string;
  runtimeStatusColor: TagProps["color"];
};

export type IntakeDocumentSetSummary = {
  documentSetId: string;
  documentCount: number;
  parsedCompletedCount: number;
  parsedFailedCount: number;
  skippedCount: number;
  pendingCount: number;
  canEnterRuntimeCount: number;
  blockedCount: number;
};

export type IntakePreflightSummary = {
  formatAvailability: IntakeAvailability;
  structureAvailability: IntakeAvailability;
  canEnterExtraction: boolean;
  issues: string[];
};

export type IntakeModuleOutput = IntakeDocumentSetSummary;
