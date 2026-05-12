import type { KnowledgeArchive } from "../../../../lib/api";

export type KnowledgeBaseManagementListItem = KnowledgeArchive;

export type KnowledgeBaseManagementActions = {
  refresh: () => Promise<void>;
  enterWorkspace: (archiveId: string) => void;
  openIntake: (archiveId: string) => void;
};
