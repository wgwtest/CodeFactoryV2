import { useEffect, useState } from "react";
import type { ArchiveKnowledgeEntity, ArchiveKnowledgeGraph, ArchiveKnowledgeSummary } from "../lib/api";
import { api } from "../lib/api";
import { KnowledgeGraph } from "../components/KnowledgeGraph";
import { ValidationWorkspace } from "../components/ValidationWorkspace";

const archiveId = "20161116-nas";

export function KnowledgeGraphPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<ArchiveKnowledgeSummary | null>(null);
  const [graph, setGraph] = useState<ArchiveKnowledgeGraph | null>(null);
  const [entities, setEntities] = useState<ArchiveKnowledgeEntity[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function loadArchiveKnowledge() {
      try {
        const [summaryResponse, graphResponse, entitiesResponse] = await Promise.all([
          api.get<ArchiveKnowledgeSummary>(`/knowledge/archive/${archiveId}/summary`),
          api.get<ArchiveKnowledgeGraph>(`/knowledge/archive/${archiveId}/graph`),
          api.get<ArchiveKnowledgeEntity[]>(`/knowledge/archive/${archiveId}/entities`),
        ]);
        if (cancelled) {
          return;
        }
        setSummary(summaryResponse.data);
        setGraph(graphResponse.data);
        setEntities(entitiesResponse.data);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载档案知识失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadArchiveKnowledge();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <ValidationWorkspace
      title="知识图谱"
      description="浏览从 20161116 NAS 架构资料集中提取出的实体、架构产物和关联关系。"
      stats={
        summary
          ? [
              { title: "文档", value: summary.document_count },
              { title: "实体", value: summary.entity_count },
              { title: "事件", value: summary.event_count },
              { title: "流程", value: summary.process_count },
            ]
          : []
      }
    >
      <KnowledgeGraph archiveId={archiveId} entities={entities} error={error} graph={graph} loading={loading} summary={summary} />
    </ValidationWorkspace>
  );
}
