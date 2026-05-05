import { api } from "./api";
import type { P3DesignLabInputPackage, P3DesignLabSession } from "./api";

export function getSoftwareDesignV2InputPackages() {
  return api.get<{ items: P3DesignLabInputPackage[] }>("/software-design-v2/input-packages");
}

export function createSoftwareDesignV2Session(payload: {
  input_package_id: string;
  generation_policy: Record<string, string>;
}) {
  return api.post<P3DesignLabSession>("/software-design-v2/sessions", payload);
}

export function generateSoftwareDesignV2Session(sessionId: string) {
  return api.post<P3DesignLabSession>(`/software-design-v2/sessions/${sessionId}/generate`);
}
