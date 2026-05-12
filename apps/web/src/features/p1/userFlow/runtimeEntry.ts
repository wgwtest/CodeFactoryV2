import type { ArchiveDocumentRuntimeContract, KnowledgeArchive, KnowledgeArchiveBuildStateDocument } from "../../../lib/api";

export type P1UserDataSource = "live" | "fixture" | "mock_fallback";

export type P1UserDocumentState = {
  label: string;
  color: string;
  description: string;
};

export function resolveP1RunId(archive: KnowledgeArchive | null | undefined) {
  const policySnapshot = archive?.build_state?.policy_snapshot;
  return policySnapshot?.run_id ?? policySnapshot?.snapshot_id ?? archive?.build_state?.started_at ?? null;
}

export function buildP1RuntimeWorkbenchUrl(params: {
  archiveId: string | null | undefined;
  documentId: string;
  runId?: string | null;
}) {
  const search = new URLSearchParams();
  if (params.archiveId) {
    search.set("archive_id", params.archiveId);
  }
  search.set("document_id", params.documentId);
  if (params.runId) {
    search.set("run_id", params.runId);
  }
  return `/archives?${search.toString()}`;
}

export function createP1DeepLinkedDocument(params: {
  documentId: string;
  title?: string | null;
  archive?: KnowledgeArchive | null;
  runtime?: ArchiveDocumentRuntimeContract | null;
}): KnowledgeArchiveBuildStateDocument {
  const runtimeState = params.runtime?.status === "running" ? "running" : params.runtime?.status === "blocked" ? "failed" : "pending";
  return {
    document_id: params.documentId,
    path: "",
    title: params.title ?? params.runtime?.document_title ?? params.documentId,
    file_type: "unknown",
    source_archive: params.archive?.name ?? params.archive?.archive_id ?? "runtime-link",
    state: runtimeState,
  };
}

export function getP1UserDataSourceLabel(source: P1UserDataSource) {
  if (source === "live") return "live";
  if (source === "fixture") return "fixture";
  return "mock_fallback";
}

export function describeP1UserDocumentState(params: {
  includedInArchive?: boolean | null;
  runtimeDocument?: KnowledgeArchiveBuildStateDocument | null;
}) {
  const runtimeState = params.runtimeDocument?.state;
  if (runtimeState === "running") {
    return {
      label: "机器抽取中",
      color: "processing",
      description: "后端运行态正在推进，可进入单文档实时工作台查看。",
    } satisfies P1UserDocumentState;
  }
  if (runtimeState === "failed") {
    return {
      label: "抽取阻断",
      color: "error",
      description: "机器抽取未完成，需要查看阻断原因或调整策略后重跑。",
    } satisfies P1UserDocumentState;
  }
  if (params.includedInArchive === true) {
    return {
      label: "正式入库",
      color: "success",
      description: "该文档知识已进入当前知识库正式结果。",
    } satisfies P1UserDocumentState;
  }
  if (params.includedInArchive === false) {
    return {
      label: "等待抽取",
      color: "default",
      description: "该文档已在清单中，但尚未形成正式知识。",
    } satisfies P1UserDocumentState;
  }
  return {
    label: "发布候选待确认",
    color: "purple",
    description: "机器结果可作为发布候选，但不等同于正式入库。",
  } satisfies P1UserDocumentState;
}
