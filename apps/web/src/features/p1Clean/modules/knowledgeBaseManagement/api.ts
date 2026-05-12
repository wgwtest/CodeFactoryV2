import { activateKnowledgeArchive, createKnowledgeArchive, getKnowledgeArchives } from "../../../../lib/archives";

export const knowledgeBaseManagementApi = {
  listArchives: getKnowledgeArchives,
  createArchive: createKnowledgeArchive,
  activateArchive: activateKnowledgeArchive,
};
