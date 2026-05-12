import { api } from "../../../../lib/api";
import { getArchivePublication } from "../../../../lib/archiveKnowledge";
import type { P1ResponseEnvelope, PublicationCandidateSnapshot } from "../../../p1/contracts";

export async function getPublicationCandidateSnapshot(
  archiveId: string,
  runtimeSnapshotId?: string | null,
  policyPackageVersionId?: string | null,
): Promise<P1ResponseEnvelope<PublicationCandidateSnapshot>> {
  const { data } = await api.get<P1ResponseEnvelope<PublicationCandidateSnapshot>>(
    `/p1/archives/${archiveId}/publication-candidates/latest`,
    {
      params: {
        ...(runtimeSnapshotId ? { runtime_snapshot_id: runtimeSnapshotId } : {}),
        ...(policyPackageVersionId ? { policy_package_version_id: policyPackageVersionId } : {}),
      },
    },
  );
  return data;
}

export const publicationApi = {
  getArchivePublication,
  getPublicationCandidateSnapshot,
};
