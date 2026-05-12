import { api } from "../../../../lib/api";
import { getArchiveGraph, getArchiveSummary } from "../../../../lib/archiveKnowledge";
import type { QualityGraphReportEnvelope } from "./types";

export type QualityGraphReportQuery = {
  archiveId: string;
  runtimeSnapshotId: string;
  policyPackageVersionId: string;
};

export function getQualityGraphReport({
  archiveId,
  runtimeSnapshotId,
  policyPackageVersionId,
}: QualityGraphReportQuery) {
  return api.get<QualityGraphReportEnvelope>(`/p1/archives/${encodeURIComponent(archiveId)}/quality-graph/report`, {
    params: {
      runtime_snapshot_id: runtimeSnapshotId,
      policy_package_version_id: policyPackageVersionId,
    },
  });
}

export const qualityGraphApi = {
  getArchiveGraph,
  getArchiveSummary,
  getQualityGraphReport,
};
