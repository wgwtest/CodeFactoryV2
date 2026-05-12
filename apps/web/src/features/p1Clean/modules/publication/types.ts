export type PublicationCandidateState =
  | "machine_candidate_created"
  | "governance_pending"
  | "formalized"
  | "blocked_by_quality"
  | "stale_after_policy_change"
  | "candidate"
  | "waiting_governance"
  | "approved"
  | "rejected";

export type PublicationModuleOutput = {
  publicationSnapshotId: string;
};

export type PublicationStateLabel = {
  label: string;
  color: "default" | "blue" | "green" | "gold" | "red";
};
