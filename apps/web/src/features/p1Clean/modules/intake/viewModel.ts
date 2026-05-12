import type {
  IntakeAvailability,
  IntakeContractDocument,
  IntakeContractSnapshot,
  IntakeDocumentRow,
  IntakeDocumentSetSummary,
  IntakeParseStatus,
  IntakePreflightSummary,
} from "./types";

const supportedFileTypes = new Set(["pdf", "doc", "docx", "xlsx", "xls"]);

const parseStatusMeta: Record<
  IntakeParseStatus,
  { label: string; color: IntakeDocumentRow["parseStatusColor"] }
> = {
  pending: { label: "待解析", color: "default" },
  running: { label: "解析中", color: "blue" },
  completed: { label: "解析完成", color: "green" },
  failed: { label: "解析失败", color: "red" },
  skipped: { label: "已跳过", color: "orange" },
};

export function buildDocumentSetId(archiveId: string) {
  return `${archiveId}:document-set`;
}

function normalizeFileType(fileType: string | null | undefined) {
  return (fileType ?? "").replace(/^\./, "").trim().toLowerCase();
}

function resolveRuntimeStatus(document: IntakeContractDocument) {
  if (document.can_enter_runtime) {
    return { label: "可进入运行", color: "green" as IntakeDocumentRow["runtimeStatusColor"] };
  }
  if (document.parse_status === "failed") {
    return { label: "解析阻断", color: "red" as IntakeDocumentRow["runtimeStatusColor"] };
  }
  if (document.parse_status === "running") {
    return { label: "等待解析完成", color: "blue" as IntakeDocumentRow["runtimeStatusColor"] };
  }
  if (document.parse_status === "skipped") {
    return { label: "未纳入集合", color: "orange" as IntakeDocumentRow["runtimeStatusColor"] };
  }
  return { label: "暂不可进入", color: "orange" as IntakeDocumentRow["runtimeStatusColor"] };
}

export function buildIntakeRows(snapshot: IntakeContractSnapshot): IntakeDocumentRow[] {
  return snapshot.documents.map((document) => {
    const parseStatus = document.parse_status;
    const parseMeta = parseStatusMeta[parseStatus];
    const runtimeStatus = resolveRuntimeStatus(document);

    return {
      id: document.document_id,
      documentId: document.document_id,
      title: document.title,
      fileName: document.file_name,
      fileType: normalizeFileType(document.file_type).toUpperCase() || "UNKNOWN",
      sourcePath: document.source_path,
      parseStatus,
      parseStatusLabel: parseMeta.label,
      parseStatusColor: parseMeta.color,
      parseError: document.parse_error,
      segmentCount: document.segment_count,
      anchorCount: document.anchor_count,
      canEnterRuntime: document.can_enter_runtime,
      runtimeStatus: runtimeStatus.label,
      runtimeStatusColor: runtimeStatus.color,
    };
  });
}

export function buildDocumentSetSummary(snapshot: IntakeContractSnapshot): IntakeDocumentSetSummary {
  const skippedCount = snapshot.documents.filter((document) => document.parse_status === "skipped").length;

  return {
    documentSetId: snapshot.document_set_id || buildDocumentSetId(snapshot.archive_id),
    documentCount: snapshot.summary.document_count,
    parsedCompletedCount: snapshot.summary.parsed_completed_count,
    parsedFailedCount: snapshot.summary.parsed_failed_count,
    skippedCount,
    pendingCount: snapshot.summary.pending_count,
    canEnterRuntimeCount: snapshot.summary.can_enter_runtime_count,
    blockedCount: snapshot.summary.blocked_count,
  };
}

function resolveAvailability(hasFailure: boolean, hasWarning: boolean): IntakeAvailability {
  if (hasFailure) return "unavailable";
  if (hasWarning) return "warning";
  return "available";
}

export function buildPreflightSummary(snapshot: IntakeContractSnapshot): IntakePreflightSummary {
  const rows = buildIntakeRows(snapshot);
  const issues = [...snapshot.preflight_issues];
  const unsupportedRows = rows.filter((row) => !supportedFileTypes.has(row.fileType.toLowerCase()));
  const blockedRows = rows.filter((row) => !row.canEnterRuntime);
  const failedRows = rows.filter((row) => row.parseStatus === "failed");

  if (rows.length === 0) {
    issues.push("当前文档集合为空");
  }
  if (unsupportedRows.length > 0) {
    issues.push(`存在 ${unsupportedRows.length} 个暂不支持的文件格式`);
  }
  for (const row of blockedRows) {
    if (row.parseError) {
      issues.push(`${row.fileName}：${row.parseError}`);
    }
  }

  const uniqueIssues = Array.from(new Set(issues));
  const hasFormatFailure = rows.length === 0 || unsupportedRows.length > 0;
  const hasStructureFailure = rows.length === 0 || blockedRows.length > 0 || failedRows.length > 0;
  const hasWarning = uniqueIssues.length > 0;

  return {
    formatAvailability: resolveAvailability(hasFormatFailure, hasWarning),
    structureAvailability: resolveAvailability(hasStructureFailure, hasWarning),
    canEnterExtraction: rows.length > 0 && blockedRows.length === 0 && unsupportedRows.length === 0,
    issues: uniqueIssues,
  };
}
