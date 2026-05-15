import { api } from "./api";
import type { P3DesignLabInputPackage, P3DesignLabSession } from "./api";

export function getSoftwareDesignV2InputPackages() {
  return api.get<{ items: P3DesignLabInputPackage[] }>("/software-design-v2/input-packages");
}

export function createSoftwareDesignV2Session(payload: {
  input_package_id: string;
  design_title: string;
  version_label: string;
  generation_policy: Record<string, string>;
}) {
  return api.post<P3DesignLabSession>("/software-design-v2/sessions", payload);
}

export function runSoftwareDesignV2Conversion(sessionId: string, payload: { strategy: string }) {
  return api.post<P3DesignLabSession>(`/software-design-v2/sessions/${sessionId}/conversion`, payload);
}

export function getSoftwareDesignV2Session(sessionId: string) {
  return api.get<P3DesignLabSession>(`/software-design-v2/sessions/${sessionId}`);
}

export function appendSoftwareDesignV2Turn(sessionId: string, payload: { user_input: string }) {
  return api.post<{ turn: Record<string, unknown>; session: P3DesignLabSession }>(
    `/software-design-v2/sessions/${sessionId}/turns`,
    payload,
  );
}

export function runSoftwareDesignV2Check(sessionId: string) {
  return api.post<{ session_id: string; check_result: P3DesignLabSession["check_result"]; session?: P3DesignLabSession }>(
    `/software-design-v2/sessions/${sessionId}/check`,
  );
}

export function saveSoftwareDesignV2Draft(sessionId: string) {
  return api.post<P3DesignLabSession>(`/software-design-v2/sessions/${sessionId}/save`);
}

export function generateSoftwareDesignV2Projection(sessionId: string) {
  return api.post<P3DesignLabSession>(`/software-design-v2/sessions/${sessionId}/projection`);
}

export function freezeSoftwareDesignV2Session(sessionId: string) {
  return api.post<P3DesignLabSession>(`/software-design-v2/sessions/${sessionId}/freeze`);
}

export function deleteSoftwareDesignV2Session(sessionId: string) {
  return api.delete<{ deleted_session_id: string }>(`/software-design-v2/sessions/${sessionId}`);
}
