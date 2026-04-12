import { useEffect, useState } from "react";
import { Card, Tag, Typography } from "antd";
import type {
  ArchiveKnowledgeEntity,
  ArchiveKnowledgeGraph,
  ArchiveKnowledgeSummary,
  ArchivePublicationOverview,
} from "../lib/api";
import { getArchiveEntities, getArchiveGraph, getArchivePublication, getArchiveSummary } from "../lib/archiveKnowledge";
import { KnowledgeGraph } from "../components/KnowledgeGraph";
import { ValidationWorkspace } from "../components/ValidationWorkspace";

export function KnowledgeGraphPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<ArchiveKnowledgeSummary | null>(null);
  const [graph, setGraph] = useState<ArchiveKnowledgeGraph | null>(null);
  const [entities, setEntities] = useState<ArchiveKnowledgeEntity[]>([]);
  const [publicationOverview, setPublicationOverview] = useState<ArchivePublicationOverview | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadArchiveKnowledge() {
      try {
        const [summaryResponse, graphResponse, entitiesResponse, publicationResponse] = await Promise.all([
          getArchiveSummary(),
          getArchiveGraph(),
          getArchiveEntities(),
          getArchivePublication(),
        ]);
        if (cancelled) {
          return;
        }
        setSummary(summaryResponse.data);
        setGraph(graphResponse.data);
        setEntities(entitiesResponse.data);
        setPublicationOverview(publicationResponse.data);
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
    >
      {summary ? (
        <Card
          variant="borderless"
          style={{
            borderRadius: 16,
            overflow: "hidden",
            background:
              "linear-gradient(135deg, rgba(244,248,255,0.96) 0%, rgba(238,247,241,0.96) 52%, rgba(255,250,240,0.96) 100%)",
            boxShadow: "0 10px 24px rgba(15, 23, 42, 0.06)",
          }}
          styles={{ body: { padding: "10px 14px" } }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 12,
              flexWrap: "nowrap",
              overflowX: "auto",
              paddingBottom: 2,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                flexWrap: "nowrap",
                flexShrink: 0,
                minWidth: "max-content",
              }}
            >
              <Tag
                color="processing"
                style={{
                  borderRadius: 9999,
                  paddingInline: 10,
                  lineHeight: "22px",
                  marginInlineEnd: 0,
                }}
              >
                已发布知识仓
              </Tag>
              <Typography.Title level={5} style={{ margin: 0, whiteSpace: "nowrap" }}>
                档案知识总览
              </Typography.Title>
              <Tag style={{ borderRadius: 9999, paddingInline: 10, lineHeight: "22px", marginInlineEnd: 0 }}>
                版本：{publicationOverview?.current_version?.version_label ?? "未发布"}
              </Tag>
              <Tag style={{ borderRadius: 9999, paddingInline: 10, lineHeight: "22px", marginInlineEnd: 0 }}>
                节点：{graph?.nodes.length ?? 0}
              </Tag>
              <Tag style={{ borderRadius: 9999, paddingInline: 10, lineHeight: "22px", marginInlineEnd: 0 }}>
                关系：{graph?.edges.length ?? 0}
              </Tag>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                flexWrap: "nowrap",
                flexShrink: 0,
                minWidth: "max-content",
              }}
            >
              {[
                { title: "文档", value: summary.document_count, accent: "#0f766e", tone: "rgba(20, 184, 166, 0.08)" },
                { title: "实体", value: summary.entity_count, accent: "#1d4ed8", tone: "rgba(59, 130, 246, 0.10)" },
                { title: "事件", value: summary.event_count, accent: "#b45309", tone: "rgba(245, 158, 11, 0.12)" },
                { title: "流程", value: summary.process_count, accent: "#7c3aed", tone: "rgba(139, 92, 246, 0.10)" },
              ].map((item) => (
                <div
                  key={item.title}
                  style={{
                    borderRadius: 9999,
                    padding: "5px 10px",
                    background: item.tone,
                    border: "1px solid rgba(148, 163, 184, 0.16)",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  <Typography.Text style={{ color: item.accent, fontWeight: 600, fontSize: 12, whiteSpace: "nowrap" }}>
                    {item.title}
                  </Typography.Text>
                  <Typography.Text style={{ color: "#0f172a", fontWeight: 700, fontSize: 14, whiteSpace: "nowrap" }}>
                    {item.value.toLocaleString("zh-CN")}
                  </Typography.Text>
                </div>
              ))}
            </div>
          </div>
        </Card>
      ) : null}
      <KnowledgeGraph entities={entities} error={error} graph={graph} loading={loading} summary={summary} />
    </ValidationWorkspace>
  );
}
