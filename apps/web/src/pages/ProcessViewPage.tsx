import { useEffect, useState } from "react";
import { Card, Typography } from "antd";

import type { ArchiveKnowledgeProcess } from "../lib/api";
import { api } from "../lib/api";
import { ProcessFlow } from "../components/ProcessFlow";

const archiveId = "20161116-nas";

export function ProcessViewPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processes, setProcesses] = useState<ArchiveKnowledgeProcess[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function loadProcesses() {
      try {
        const response = await api.get<ArchiveKnowledgeProcess[]>(`/knowledge/archive/${archiveId}/processes`);
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
    <Card>
      <Typography.Title level={3}>流程视图</Typography.Title>
      <Typography.Paragraph>
        查看从 NAS 档案资料中归纳出的流程知识，包括互操作、治理和路线图规划等流程。
      </Typography.Paragraph>
      <ProcessFlow error={error} loading={loading} processes={processes} />
    </Card>
  );
}
