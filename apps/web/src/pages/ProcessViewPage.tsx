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
      title="流程链路视图"
      description="查看已发布流程清单，并下钻流程证据、关联对象、业务关系结构与关系邻域。"
      stats={[{ title: "流程总数", value: processes.length }]}
    >
      <ProcessFlow error={error} loading={loading} processes={processes} />
    </ValidationWorkspace>
  );
}
