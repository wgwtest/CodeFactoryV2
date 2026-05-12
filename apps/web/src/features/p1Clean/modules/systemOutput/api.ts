import { api } from "../../../../lib/api";
import { getArchiveGraph, getArchivePublication, getArchiveSummary } from "../../../../lib/archiveKnowledge";
import type { P1ResponseEnvelope, PublicationCandidateSnapshot } from "../../../p1/contracts";
import type { SystemOutputContract } from "./types";

export function getPublicationCandidateSnapshot(
  archiveId: string,
  runtimeSnapshotId?: string | null,
  policyPackageVersionId?: string | null,
) {
  return api.get<P1ResponseEnvelope<PublicationCandidateSnapshot>>(
    `/p1/archives/${archiveId}/publication-candidates/latest`,
    {
      params: {
        ...(runtimeSnapshotId ? { runtime_snapshot_id: runtimeSnapshotId } : {}),
        ...(policyPackageVersionId ? { policy_package_version_id: policyPackageVersionId } : {}),
      },
    },
  );
}

export function getSystemOutputContract(archiveId: string, publicationSnapshotId?: string | null) {
  return api.get<P1ResponseEnvelope<SystemOutputContract>>(`/p1/archives/${archiveId}/system-output`, {
    params: publicationSnapshotId ? { publication_snapshot_id: publicationSnapshotId } : undefined,
  });
}

export const systemOutputApi = {
  getArchiveSummary,
  getArchiveGraph,
  getArchivePublication,
  getPublicationCandidateSnapshot,
  getSystemOutputContract,
};
