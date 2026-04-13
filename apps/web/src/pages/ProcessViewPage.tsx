import { useEffect, useState } from "react";

import { ProcessFlow } from "../components/ProcessFlow";
import { ValidationWorkspace } from "../components/ValidationWorkspace";
import { useArchiveContext } from "../context/ArchiveContext";
import { getArchiveProcesses } from "../lib/archiveKnowledge";
import type { ArchiveKnowledgeProcess } from "../lib/api";

export function ProcessViewPage() {
  const { activeArchive, activeArchiveId } = useArchiveContext();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processes, setProcesses] = useState<ArchiveKnowledgeProcess[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function loadProcesses() {
      if (!activeArchiveId) {
        setProcesses([]);
        setLoading(false);
        return;
      }

      try {
        const response = await getArchiveProcesses(activeArchiveId);
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
  }, [activeArchiveId]);

  return (
    <ValidationWorkspace
      title="流程视图"
      description={`查看已发布流程清单，并下钻流程证据、关联对象、业务关系结构与关系邻域。${activeArchive ? ` 当前知识库：${activeArchive.name}。` : ""}`}
      stats={[{ title: "流程总数", value: processes.length }]}
    >
      <ProcessFlow archiveId={activeArchiveId} error={error} loading={loading} processes={processes} />
    </ValidationWorkspace>
  );
}
