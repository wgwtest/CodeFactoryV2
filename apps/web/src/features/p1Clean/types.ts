import type { ComponentType } from "react";

import type { KnowledgeArchive } from "../../lib/api";

export type P1WorkspaceContext = {
  archiveId: string;
  archive: KnowledgeArchive;
  policyPackageVersionId: string | null;
  runtimeSnapshotId: string | null;
  documentSetId: string | null;
  publicationSnapshotId: string | null;
};

export type P1ModuleId =
  | "knowledgeBaseManagement"
  | "intake"
  | "policyRules"
  | "runtime"
  | "qualityGraph"
  | "knowledgeResults"
  | "publication"
  | "systemOutput";

export type P1ModuleLifecycle = "active" | "scaffold" | "reference";

export type P1ContextKey =
  | "archiveId"
  | "policyPackageVersionId"
  | "runtimeSnapshotId"
  | "documentSetId"
  | "publicationSnapshotId";

export type P1ModuleContract = {
  inputs: P1ContextKey[];
  outputs: P1ContextKey[];
  owns: string[];
  consumes: string[];
};

export type P1ModulePageProps = {
  context: P1WorkspaceContext;
};

export type P1ModuleDefinition = {
  id: P1ModuleId;
  navLabel: string;
  title: string;
  route: string;
  order: number;
  lifecycle: P1ModuleLifecycle;
  summary: string;
  contract: P1ModuleContract;
  Page: ComponentType<P1ModulePageProps>;
};

export type P1ModuleTestEntry = {
  moduleId: P1ModuleId;
  smokeRoute: string;
  verifies: string[];
};
