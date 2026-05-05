import { api } from "./api";
import type {
  P1DomainKnowledgeArchive,
  P1DomainKnowledgeCatalog,
  P1KnowledgeProviderRegistration,
  P1SimCallLogEnvelope,
} from "./api";

export function getXXP1SimDomains() {
  return api.get<P1DomainKnowledgeCatalog>("/xx-p1-sim/domains");
}

export function getXXP1SimDomainKnowledge(domainId: string) {
  return api.get<P1DomainKnowledgeArchive>(`/xx-p1-sim/domains/${domainId}/knowledge`);
}

export function getXXP1SimLogs() {
  return api.get<P1SimCallLogEnvelope>("/xx-p1-sim/logs");
}

export function registerXXP1Sim() {
  return api.post<P1KnowledgeProviderRegistration>("/xx-p1-sim/register");
}

export function resetXXP1SimSeed() {
  return api.post<{ provider_id: string; seed: string; archive_version: string; log_count: number }>("/xx-p1-sim/reset");
}
