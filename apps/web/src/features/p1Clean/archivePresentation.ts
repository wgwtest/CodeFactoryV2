import type { KnowledgeArchive } from "../../lib/api";

export function getArchiveStatusLabel(archive: KnowledgeArchive) {
  if (archive.build_state?.status === "running" || archive.status === "extracting") return "运行中";
  if (archive.status === "ready") return "已就绪";
  if (archive.status === "error") return "异常";
  return "空库";
}

export function getArchiveStatusColor(archive: KnowledgeArchive) {
  if (archive.build_state?.status === "running" || archive.status === "extracting") return "blue";
  if (archive.status === "ready") return "green";
  if (archive.status === "error") return "red";
  return "default";
}

export function getArchivePolicyLabel(archive: KnowledgeArchive) {
  const snapshot = archive.build_state?.policy_snapshot;
  return snapshot?.policy_package_name ?? snapshot?.policy_package_id ?? "未绑定策略";
}

export function getArchiveSnapshotLabel(archive: KnowledgeArchive) {
  const snapshot = archive.build_state?.policy_snapshot;
  return snapshot?.snapshot_id ?? "未生成";
}

export function getArchiveTopic(archive: KnowledgeArchive) {
  if (archive.summary && archive.summary.entity_count + archive.summary.event_count + archive.summary.process_count > 0) {
    return `实体 ${archive.summary.entity_count} / 事件 ${archive.summary.event_count} / 流程 ${archive.summary.process_count}`;
  }
  if (archive.build_state?.current_stage_label) {
    return `当前阶段：${archive.build_state.current_stage_label}`;
  }
  return "等待资料接入与抽取";
}
