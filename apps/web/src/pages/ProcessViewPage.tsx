import { useEffect, useState } from "react";
import type { ArchiveKnowledgeProcess } from "../lib/api";
import { getArchiveProcesses } from "../lib/archiveKnowledge";
import { ProcessFlow } from "../components/ProcessFlow";
import { ValidationWorkspace } from "../components/ValidationWorkspace";

export function ProcessViewPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processes, setProcesses] = useState<ArchiveKnowledgeProcess[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function loadProcesses() {
      try {
        const response = await getArchiveProcesses();
        if (cancelled) {
          return;
        }
        setProcesses(response.data);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载档案流程失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadProcesses();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <ValidationWorkspace
      title="流程视图"
      description="查看从 NAS 档案资料中归纳出的流程知识，包括互操作、治理和路线图规划等流程。"
      stats={[{ title: "流程总数", value: processes.length }]}
    >
      <ProcessFlow error={error} loading={loading} processes={processes} />
    </ValidationWorkspace>
  );
}
