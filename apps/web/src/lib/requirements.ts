import { api } from "./api";
import type {
  RequirementFormalElement,
  RequirementSpecDetail,
  RequirementSpecSummary,
  RequirementSpecWriteInput,
} from "./api";

const DEFAULT_ARCHIVE_ID = "20161116-nas";

export function getRequirementSpecs() {
  return api.get<RequirementSpecSummary[]>("/requirements/specs");
}

export function getRequirementSpec(specId: string) {
  return api.get<RequirementSpecDetail>(`/requirements/specs/${specId}`);
}

export function createRequirementSpec(payload: RequirementSpecWriteInput) {
  return api.post<RequirementSpecDetail>("/requirements/specs", payload);
}

export function updateRequirementSpec(specId: string, payload: RequirementSpecWriteInput) {
  return api.put<RequirementSpecDetail>(`/requirements/specs/${specId}`, payload);
}

export function getRequirementFormalElements(
  itemType: "entity" | "process" = "entity",
  archiveId = DEFAULT_ARCHIVE_ID,
) {
  return api.get<RequirementFormalElement[]>(
    `/requirements/formal-elements?item_type=${itemType}&archive_id=${archiveId}`,
  );
}
