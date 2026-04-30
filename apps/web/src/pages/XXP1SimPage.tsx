import { type ReactNode, useEffect, useMemo, useState } from "react";
import { Alert, Button, Empty, Space, Spin, Tag, Typography } from "antd";

import type {
  P1DomainKnowledgeArchive,
  P1DomainKnowledgeCatalog,
  P1DomainKnowledgeCatalogItem,
  P1SimCallLog,
} from "../lib/api";
import {
  getXXP1SimDomainKnowledge,
  getXXP1SimDomains,
  getXXP1SimLogs,
  registerXXP1Sim,
  resetXXP1SimSeed,
} from "../lib/xxP1Sim";
import "./XXP1SimPage.css";

const { Text, Title } = Typography;

export function XXP1SimPage() {
  const [catalog, setCatalog] = useState<P1DomainKnowledgeCatalog | null>(null);
  const [selectedDomainId, setSelectedDomainId] = useState("airspace-planning");
  const [archive, setArchive] = useState<P1DomainKnowledgeArchive | null>(null);
  const [logs, setLogs] = useState<P1SimCallLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedDomain = useMemo(
    () => catalog?.items.find((item) => item.domain_id === selectedDomainId) ?? catalog?.items[0] ?? null,
    [catalog, selectedDomainId],
  );

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        const catalogResponse = await getXXP1SimDomains();
        if (cancelled) {
          return;
        }
        const nextCatalog = catalogResponse.data;
        const nextDomainId = nextCatalog.items[0]?.domain_id ?? "airspace-planning";
        setCatalog(nextCatalog);
        setSelectedDomainId(nextDomainId);
        const [archiveResponse, logsResponse] = await Promise.all([
          getXXP1SimDomainKnowledge(nextDomainId),
          getXXP1SimLogs(),
        ]);
        if (cancelled) {
          return;
        }
        setArchive(archiveResponse.data);
        setLogs(logsResponse.data.items);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载 XX-P1-Sim 失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSelectDomain(domain: P1DomainKnowledgeCatalogItem) {
    try {
      setSelectedDomainId(domain.domain_id);
      const response = await getXXP1SimDomainKnowledge(domain.domain_id);
      setArchive(response.data);
      setError(null);
    } catch (selectError) {
      setError(selectError instanceof Error ? selectError.message : "加载知识包失败");
    }
  }

  async function handleRegister() {
    try {
      setActing(true);
      const response = await registerXXP1Sim();
      setCatalog((current) => (current ? { ...current, provider: response.data } : current));
      setMessage("已注册到 P2");
      setError(null);
    } catch (registerError) {
      setError(registerError instanceof Error ? registerError.message : "注册到 P2 失败");
    } finally {
      setActing(false);
    }
  }

  async function handleReset() {
    try {
      setActing(true);
      const response = await resetXXP1SimSeed();
      const logsResponse = await getXXP1SimLogs();
      setLogs(logsResponse.data.items);
      setMessage(`固定种子已重置：${response.data.seed}`);
      setError(null);
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "重置种子失败");
    } finally {
      setActing(false);
    }
  }

  return (
    <main className="xx-p1-sim-page">
      <header className="xx-p1-sim-topbar">
        <div className="xx-p1-sim-brand">
          <div className="xx-p1-sim-mark">SIM</div>
          <div>
            <Title level={2}>XX-P1-Sim</Title>
            <Text type="secondary">模拟 P1 上游知识服务：P2 通过服务接口查询领域知识</Text>
          </div>
        </div>
        <Space wrap>
          <Button onClick={() => setMessage("最近调用日志已在主工作区右侧展示")}>查看日志</Button>
          <Button loading={acting} onClick={() => void handleReset()}>
            重置种子
          </Button>
          <Button type="primary" loading={acting} onClick={() => void handleRegister()}>
            注册到 P2
          </Button>
        </Space>
      </header>

      {message ? <Alert type="success" showIcon message={message} /> : null}
      {error ? <Alert type="error" showIcon message={error} /> : null}

      {loading ? (
        <Spin />
      ) : catalog ? (
        <section className="xx-p1-sim-layout">
          <aside className="xx-p1-sim-sidebar" aria-label="当前模拟服务">
            <div>
              <Title level={4}>当前模拟服务</Title>
              <Text type="secondary">这个页面只扮演 P1 知识服务。P2 通过接口读取领域知识，后续需求规格仍由专家工作台生成。</Text>
            </div>
            <SummaryRow label="连接状态" value={catalog.provider.status === "online" ? "已注册到 P2" : "未注册"} active />
            <SummaryRow label="服务标识" value={catalog.provider.provider_id} />
            <SummaryRow label="领域知识" value={`${catalog.items.length} 组`} />
            <SummaryRow label="知识版本" value={`${catalog.provider.version} 固定`} />
            <SummaryRow label="最近调用" value={`${logs.length} 条`} />
            <Text type="secondary">不提供目标软件目录，不模拟专家回答，不生成需求规格正文。</Text>
          </aside>

          <div className="xx-p1-sim-workspace">
            <div className="xx-p1-sim-workspace-head">
              <Space wrap>
                <Text strong>P1 服务接口模拟台</Text>
                <Tag color="green">P2 可调用</Tag>
                <Tag color="blue">领域知识源</Tag>
              </Space>
              <Space wrap>
                <Tag>service_id: {catalog.provider.provider_id}</Tag>
                <Tag color="orange">固定种子 v1.0</Tag>
              </Space>
            </div>

            <div className="xx-p1-sim-grid">
              <section className="xx-p1-sim-panel">
                <PanelHead title="P1 服务接口" subtitle="P2 调用这些接口来发现领域、读取知识包和核对模拟器状态。" tag="service online" />
                <div className="xx-p1-sim-interface-list">
                  <InterfaceRow method="POST" path="/api/xx-p1-sim/register" note="注册给 P2" />
                  <InterfaceRow method="GET" path="/api/xx-p1-sim/domains" note="领域列表" />
                  <InterfaceRow method="GET" path="/api/xx-p1-sim/domains/{domain_id}/knowledge" note="知识包" />
                  <InterfaceRow method="GET" path="/api/xx-p1-sim/logs" note="调用日志" />
                </div>
              </section>

              <section className="xx-p1-sim-panel">
                <PanelHead title="最近调用日志" subtitle="记录 P2 什么时候调用了哪个接口，方便联调时核对。" tag={`${logs.length} 条`} />
                <div className="xx-p1-sim-log-list">
                  {logs.length ? logs.slice(-5).map((item) => <LogRow key={item.call_id} item={item} />) : <Empty description="暂无调用日志" />}
                </div>
              </section>

              <section className="xx-p1-sim-panel xx-p1-sim-wide">
                <PanelHead title="领域知识目录" subtitle="这里是 P1 领域知识，不是软件目录，也不是 P2 文档样板。" tag={`${catalog.items.length} 组领域知识`} />
                <div className="xx-p1-sim-domain-list">
                  {catalog.items.map((domain) => (
                    <button
                      type="button"
                      key={domain.domain_id}
                      className={`xx-p1-sim-domain-card${domain.domain_id === selectedDomainId ? " is-active" : ""}`}
                      onClick={() => void handleSelectDomain(domain)}
                    >
                      <span>
                        <Text strong>{domain.domain_name}</Text>
                        <Text type="secondary">{domain.domain_summary}</Text>
                        <span className="xx-p1-sim-domain-meta">
                          <Tag>概念 {domain.concept_count}</Tag>
                          <Tag>规则 {domain.rule_count}</Tag>
                          <Tag>证据 {domain.evidence_count}</Tag>
                        </span>
                      </span>
                      <Tag color={domain.domain_id === selectedDomainId ? "green" : "default"}>可查询</Tag>
                    </button>
                  ))}
                </div>
              </section>

              <section className="xx-p1-sim-panel xx-p1-sim-wide">
                <PanelHead title={selectedDomain ? selectedDomain.domain_name.replace("领域知识", "知识包预览") : "知识包预览"} subtitle="预览 P1 会给 P2 的知识，不含目标软件名。" tag={`knowledge_archive ${archive?.archive_version ?? "v1.0"}`} />
                {archive ? <ArchivePreview archive={archive} /> : <Empty description="请选择领域知识" />}
              </section>
            </div>
          </div>
        </section>
      ) : (
        <Empty description="未加载到 P1 模拟服务" />
      )}
    </main>
  );
}

function SummaryRow({ label, value, active = false }: { label: string; value: string; active?: boolean }) {
  return (
    <div className={`xx-p1-sim-summary-row${active ? " is-active" : ""}`}>
      <Text strong>{label}</Text>
      <Text>{value}</Text>
    </div>
  );
}

function PanelHead({ title, subtitle, tag }: { title: string; subtitle: string; tag: string }) {
  return (
    <div className="xx-p1-sim-panel-head">
      <div>
        <Title level={4}>{title}</Title>
        <Text type="secondary">{subtitle}</Text>
      </div>
      <Tag color="green">{tag}</Tag>
    </div>
  );
}

function InterfaceRow({ method, path, note }: { method: string; path: string; note: string }) {
  return (
    <div className="xx-p1-sim-interface-row">
      <Text strong>{method}</Text>
      <code>{path}</code>
      <Text>{note}</Text>
    </div>
  );
}

function LogRow({ item }: { item: P1SimCallLog }) {
  const time = item.called_at.slice(11, 19);
  return (
    <div className="xx-p1-sim-log-row">
      <Text strong>{time}</Text>
      <code>{item.path}</code>
      <Text>{item.status_code}</Text>
    </div>
  );
}

function ArchivePreview({ archive }: { archive: P1DomainKnowledgeArchive }) {
  const process = archive.processes[0];
  return (
    <div className="xx-p1-sim-preview-grid">
      <PreviewCard title="概念">
        <Text>{archive.concepts.map((item) => item.name).join("、")}</Text>
      </PreviewCard>
      <PreviewCard title="规则">
        <Text>{archive.rules[0]?.description ?? "暂无规则"}</Text>
      </PreviewCard>
      <PreviewCard title="流程">
        <Text>{process ? process.steps.join(" -> ") : "暂无流程"}</Text>
      </PreviewCard>
    </div>
  );
}

function PreviewCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="xx-p1-sim-preview-card">
      <Text strong>{title}</Text>
      <div>{children}</div>
    </div>
  );
}
