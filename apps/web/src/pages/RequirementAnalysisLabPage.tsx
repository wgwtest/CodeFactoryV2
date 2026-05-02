import { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Button, Input, Space, Spin, Tag, Typography } from "antd";

import type {
  RequirementAnalysisOrchestrator,
  RequirementAnalysisOrchestratorEnvelope,
  RequirementAnalysisProviderLog,
  RequirementAnalysisProvider,
  RequirementAnalysisQuickOption,
  RequirementAnalysisSession,
  RequirementAnalysisSpecTreeNode,
  RequirementAnalysisTurn,
} from "../lib/api";
import {
  createRequirementAnalysisSession,
  createRequirementAnalysisTurn,
  getRequirementAnalysisOrchestrators,
  getRequirementAnalysisProviders,
} from "../lib/requirementAnalysis";
import "./RequirementAnalysisLabPage.css";

const { Text, Title } = Typography;
const { TextArea } = Input;

const DEFAULT_TOPIC = "空域运算软件需求规格探索";
const DEFAULT_TEMPLATE = "81433号";
const DEFAULT_KNOWLEDGE = "airspace-domain-demo";
const DEFAULT_POLICY = "patch_suggestion_only";
const DEFAULT_ORCHESTRATOR_ID = "xg-heuristic-orchestrator";
type RequirementAnalysisLabTab = "config" | "session" | "turn" | "log";

export function RequirementAnalysisLabPage() {
  const [orchestratorsEnvelope, setOrchestratorsEnvelope] = useState<RequirementAnalysisOrchestratorEnvelope | null>(null);
  const [providers, setProviders] = useState<RequirementAnalysisProvider[]>([]);
  const [selectedOrchestratorId, setSelectedOrchestratorId] = useState(DEFAULT_ORCHESTRATOR_ID);
  const [selectedProviderId, setSelectedProviderId] = useState("mock");
  const [topic, setTopic] = useState(DEFAULT_TOPIC);
  const [activeTab, setActiveTab] = useState<RequirementAnalysisLabTab>("config");
  const [session, setSession] = useState<RequirementAnalysisSession | null>(null);
  const [currentTurn, setCurrentTurn] = useState<RequirementAnalysisTurn | null>(null);
  const [userInput, setUserInput] = useState("");
  const [pendingUserInput, setPendingUserInput] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        const [orchestratorsResponse, providersResponse] = await Promise.all([
          getRequirementAnalysisOrchestrators(),
          getRequirementAnalysisProviders(),
        ]);
        if (cancelled) {
          return;
        }
        setOrchestratorsEnvelope(orchestratorsResponse.data);
        setProviders(providersResponse.data.items);
        setSelectedOrchestratorId(orchestratorsResponse.data.items[0]?.orchestrator_id ?? DEFAULT_ORCHESTRATOR_ID);
        setSelectedProviderId(resolveDefaultProviderId(providersResponse.data.items));
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载 XG 需求分析组织器 Lab 失败");
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

  const selectedOrchestrator = useMemo(
    () => orchestratorsEnvelope?.items.find((item) => item.orchestrator_id === selectedOrchestratorId) ?? null,
    [orchestratorsEnvelope, selectedOrchestratorId],
  );

  const activeProvider = useMemo(
    () => providers.find((provider) => provider.provider_id === selectedProviderId) ?? null,
    [providers, selectedProviderId],
  );

  const logCount = session?.provider_logs.length ?? 0;

  async function handleStart() {
    try {
      setActing(true);
      const response = await createRequirementAnalysisSession({
        topic,
        orchestrator_id: selectedOrchestratorId,
        provider_id: selectedProviderId,
        model: selectedProviderId === "mock" ? "mock-requirement-analysis-v1" : "provider-default",
        template_id: DEFAULT_TEMPLATE,
        knowledge_package_id: DEFAULT_KNOWLEDGE,
        write_policy: DEFAULT_POLICY,
      });
      setSession(response.data);
      setCurrentTurn(response.data.turns.at(-1) ?? null);
      setError(null);
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "启动 XG 需求分析会话失败");
    } finally {
      setActing(false);
    }
  }

  async function handleSend() {
    await submitUserInput(userInput);
  }

  function handleResetSession() {
    setSession(null);
    setCurrentTurn(null);
    setUserInput("");
    setPendingUserInput(null);
    setError(null);
    setActiveTab("config");
  }

  async function submitUserInput(input: string) {
    const trimmed = input.trim();
    if (!session || !trimmed) {
      return;
    }

    try {
      setActing(true);
      setPendingUserInput(trimmed);
      setUserInput("");
      const response = await createRequirementAnalysisTurn(session.session_id, trimmed);
      setSession(response.data.session);
      setCurrentTurn(response.data.turn);
      setError(null);
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "发送当前 Turn 失败");
    } finally {
      setPendingUserInput(null);
      setActing(false);
    }
  }

  return (
    <main className="requirement-analysis-lab-page">
      <header className="requirement-analysis-lab-topbar">
        <div className="requirement-analysis-lab-brand">
          <div className="requirement-analysis-lab-mark">LAB</div>
          <div>
            <Title level={2}>P2 XG 需求分析组织器 Lab</Title>
            <Text type="secondary">独立验证问答组织器、模型 Provider 和结构化 Turn 输出，不写入正式需求规格编辑器。</Text>
          </div>
        </div>
        <Space wrap>
          <Tag color="blue">独立路由</Tag>
          <Tag color="green">可插拔组织器</Tag>
          <Tag color="orange">patch suggestion only</Tag>
        </Space>
      </header>

      {error ? <Alert type="error" showIcon message={error} /> : null}

      {loading ? (
        <section className="requirement-analysis-lab-loading">
          <Spin />
        </section>
      ) : orchestratorsEnvelope ? (
        <section className="requirement-analysis-lab-layout">
          <aside className="requirement-analysis-lab-sidebar" aria-label="XG 需求分析组织器 Lab 视图导航" role="tablist">
            <TabNode
              active={activeTab === "config"}
              badge="配置"
              onClick={() => setActiveTab("config")}
              subtitle="RequirementAnalysisOrchestrator 插槽"
              title="组织器配置"
            />
            <TabNode
              active={activeTab === "session"}
              badge={session ? "已创建" : "未创建"}
              onClick={() => setActiveTab("session")}
              subtitle="RequirementAnalysisSession"
              title="会话管理"
            />
            <TabNode
              active={activeTab === "turn"}
              badge={currentTurn?.turn_id ?? "暂无"}
              onClick={() => setActiveTab("turn")}
              subtitle="RequirementAnalysisTurn"
              title="当前 Turn"
            />
            <TabNode
              active={activeTab === "log"}
              badge={`${logCount} 条`}
              onClick={() => setActiveTab("log")}
              subtitle="Provider Calls"
              title="调用日志"
            />
          </aside>

          <section className="requirement-analysis-lab-workspace">
            {activeTab === "config" ? (
              <ConfigTab
                activeProvider={activeProvider}
                acting={acting}
                currentSession={session}
                onEnterSession={() => setActiveTab("session")}
                onProviderSelect={setSelectedProviderId}
                onStart={() => void handleStart()}
                onOrchestratorSelect={setSelectedOrchestratorId}
                onTopicChange={setTopic}
                orchestratorsEnvelope={orchestratorsEnvelope}
                providers={providers}
                selectedOrchestrator={selectedOrchestrator}
                selectedOrchestratorId={selectedOrchestratorId}
                selectedProviderId={selectedProviderId}
                topic={topic}
              />
            ) : null}
            {activeTab === "session" ? (
              <SessionTab
                acting={acting}
                currentTurn={currentTurn}
                onQuickOptionSelect={(option) => void submitUserInput(formatQuickOptionInput(option))}
                onSend={() => void handleSend()}
                pendingUserInput={pendingUserInput}
                session={session}
                setUserInput={setUserInput}
                userInput={userInput}
              />
            ) : null}
            {activeTab === "turn" ? <TurnTab currentTurn={currentTurn} onResetSession={handleResetSession} /> : null}
            {activeTab === "log" ? <LogTab logs={session?.provider_logs ?? []} /> : null}
          </section>
        </section>
      ) : null}
    </main>
  );
}

function TabNode({
  active,
  badge,
  onClick,
  title,
  subtitle,
}: {
  active: boolean;
  badge: string;
  onClick: () => void;
  title: string;
  subtitle: string;
}) {
  return (
    <button
      aria-selected={active}
      className={active ? "requirement-analysis-lab-tab is-active" : "requirement-analysis-lab-tab"}
      onClick={onClick}
      role="tab"
      type="button"
    >
      <span className="requirement-analysis-lab-tab-copy">
        <Text strong>{title}</Text>
        <Text type="secondary">{subtitle}</Text>
      </span>
      <Tag>{badge}</Tag>
    </button>
  );
}

function ConfigTab({
  activeProvider,
  acting,
  currentSession,
  onEnterSession,
  onProviderSelect,
  onStart,
  onOrchestratorSelect,
  onTopicChange,
  orchestratorsEnvelope,
  providers,
  selectedOrchestrator,
  selectedOrchestratorId,
  selectedProviderId,
  topic,
}: {
  activeProvider: RequirementAnalysisProvider | null;
  acting: boolean;
  currentSession: RequirementAnalysisSession | null;
  onEnterSession: () => void;
  onProviderSelect: (providerId: string) => void;
  onStart: () => void;
  onOrchestratorSelect: (orchestratorId: string) => void;
  onTopicChange: (topic: string) => void;
  orchestratorsEnvelope: RequirementAnalysisOrchestratorEnvelope;
  providers: RequirementAnalysisProvider[];
  selectedOrchestrator: RequirementAnalysisOrchestrator | null;
  selectedOrchestratorId: string;
  selectedProviderId: string;
  topic: string;
}) {
  return (
    <>
      <div className="requirement-analysis-lab-tab-grid is-config">
        <section className="requirement-analysis-lab-panel requirement-analysis-lab-orchestrators">
          <PanelHead title="可替换组织器" subtitle="当前只验证组织器输出协议，正式需求规格文档仍由稳定契约承接。" />
          <div className="requirement-analysis-lab-option-list">
            {orchestratorsEnvelope.items.map((orchestrator) => (
              <button
                className={
                  orchestrator.orchestrator_id === selectedOrchestratorId
                    ? "requirement-analysis-lab-option is-selected"
                    : "requirement-analysis-lab-option"
                }
                key={orchestrator.orchestrator_id}
                onClick={() => onOrchestratorSelect(orchestrator.orchestrator_id)}
                type="button"
              >
                <span>
                  <Text strong>{orchestrator.name}</Text>
                  <Text type="secondary">{orchestrator.description}</Text>
                </span>
                <Tag color={orchestrator.status === "active" ? "green" : "default"}>{orchestrator.status}</Tag>
              </button>
            ))}
          </div>
        </section>

        <section className="requirement-analysis-lab-panel">
          <PanelHead title="启动参数" subtitle="用于验证 XG 需求分析会话生命周期，不进入正式编辑器状态。" />
          <label className="requirement-analysis-lab-field">
            <Text strong>课题输入</Text>
            <Input value={topic} onChange={(event) => onTopicChange(event.target.value)} />
          </label>
          <div className="requirement-analysis-lab-provider-row">
            {providers.map((provider) => (
              <button
                className={
                  provider.provider_id === selectedProviderId ? "requirement-analysis-lab-provider is-selected" : "requirement-analysis-lab-provider"
                }
                key={provider.provider_id}
                onClick={() => onProviderSelect(provider.provider_id)}
                type="button"
              >
                <span>{provider.name}</span>
                <Tag color={provider.status === "active" ? "green" : "gold"} title={provider.status}>
                  {formatProviderStatus(provider.status)}
                </Tag>
              </button>
            ))}
          </div>
          <Button block loading={acting} onClick={onStart} type="primary">
            启动验证
          </Button>
          <Text className="requirement-analysis-lab-current-config" type="secondary">
            当前 Provider：{activeProvider?.name ?? selectedProviderId}；当前组织器：
            {selectedOrchestrator?.name ?? selectedOrchestratorId}
          </Text>
          {currentSession ? (
            <Alert
              action={
                <Button onClick={onEnterSession} size="small" type="link">
                  进入会话管理
                </Button>
              }
              className="requirement-analysis-lab-session-created"
              message={`会话已创建：${currentSession.session_id}`}
              showIcon
              type="success"
            />
          ) : null}
        </section>

        <section className="requirement-analysis-lab-panel requirement-analysis-lab-contract" data-testid="requirement-analysis-stable-contract">
          <PanelHead title="稳定契约 / 输出协议" subtitle="组织器可替换，但这些 P2 能力对象和输出字段不能被替换策略破坏。" />
          <ContractGrid stableContract={orchestratorsEnvelope.stable_contract} />
          <div className="requirement-analysis-lab-protocol-list">
            <Text strong>输出协议</Text>
            {orchestratorsEnvelope.output_protocol.map((item) => (
              <Tag key={item}>{item}</Tag>
            ))}
          </div>
          <Text className="requirement-analysis-lab-guardrail">替换组织器不能影响 P2 正式文档能力</Text>
        </section>
      </div>
    </>
  );
}

function SessionTab({
  acting,
  currentTurn,
  onQuickOptionSelect,
  onSend,
  pendingUserInput,
  session,
  setUserInput,
  userInput,
}: {
  acting: boolean;
  currentTurn: RequirementAnalysisTurn | null;
  onQuickOptionSelect: (option: RequirementAnalysisQuickOption) => void;
  onSend: () => void;
  pendingUserInput: string | null;
  session: RequirementAnalysisSession | null;
  setUserInput: (value: string) => void;
  userInput: string;
}) {
  const messageListRef = useRef<HTMLDivElement | null>(null);
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const quickOptionCount = currentTurn?.next_interaction?.options.length ?? 0;

  useEffect(() => {
    const messageList = messageListRef.current;
    if (messageList) {
      messageList.scrollTop = messageList.scrollHeight;
    }
    messageEndRef.current?.scrollIntoView({ block: "end" });
  }, [session?.messages.length, pendingUserInput, currentTurn?.turn_id, quickOptionCount]);

  return (
    <>
      <div className="requirement-analysis-lab-tab-grid is-session">
        <section className="requirement-analysis-lab-panel requirement-analysis-lab-chat">
          <PanelHead title="CLI 式问答区" subtitle={session ? `当前会话：${session.session_id}` : "请先回到“组织器配置”点击“启动验证”。"} />
          {session ? (
            <>
              <div className="requirement-analysis-lab-session-strip">
                <Text strong>会话 {session.session_id}</Text>
                <Tag>Provider {session.provider_id}</Tag>
                <Tag>Model {session.model}</Tag>
                <Tag>{formatWritePolicy(session.write_policy)}</Tag>
                <Tag>{session.topic}</Tag>
              </div>
              <div className="requirement-analysis-lab-message-list" ref={messageListRef}>
                {session.messages.map((message) => (
                  <div className={`requirement-analysis-lab-message is-${message.role}`} key={message.id}>
                    <span>{message.role}</span>
                    <p>{message.content}</p>
                  </div>
                ))}
                {pendingUserInput ? (
                  <>
                    <div className="requirement-analysis-lab-message is-user is-pending">
                      <span>user</span>
                      <p>{pendingUserInput}</p>
                    </div>
                    <div className="requirement-analysis-lab-message is-assistant is-pending">
                      <span>assistant</span>
                      <p>正在生成回应...</p>
                    </div>
                  </>
                ) : null}
                <div aria-hidden="true" className="requirement-analysis-lab-message-end" ref={messageEndRef} />
              </div>
              {!pendingUserInput && currentTurn?.next_interaction?.options.length ? (
                <QuickOptionBar disabled={acting} onSelect={onQuickOptionSelect} options={currentTurn.next_interaction.options} />
              ) : null}
              <div className="requirement-analysis-lab-command-row">
                <TextArea
                  autoSize={{ minRows: 2, maxRows: 6 }}
                  className="requirement-analysis-lab-command-input"
                  onChange={(event) => setUserInput(event.target.value)}
                  onPressEnter={(event) => {
                    if (!event.shiftKey) {
                      event.preventDefault();
                      onSend();
                    }
                  }}
                  placeholder="输入 A / 继续 / 更正式 / 或直接描述需求..."
                  value={userInput}
                />
                <Button aria-label="发送" disabled={!userInput.trim()} loading={acting} onClick={onSend} type="primary">
                  发送
                </Button>
              </div>
            </>
          ) : (
            <div className="requirement-analysis-lab-empty">
              <Text type="secondary">尚未创建 Requirement Analysis 会话。请先回到“组织器配置”点击“启动验证”。</Text>
            </div>
          )}
        </section>
        <SessionSummary session={session} />
      </div>
    </>
  );
}

function QuickOptionBar({
  disabled,
  onSelect,
  options,
}: {
  disabled: boolean;
  onSelect: (option: RequirementAnalysisQuickOption) => void;
  options: RequirementAnalysisQuickOption[];
}) {
  return (
    <div className="requirement-analysis-lab-quick-options" aria-label="快捷回复选项">
      {options.map((option, index) => {
        const recommended = option.recommended ?? index === 0;
        return (
          <div
            className={recommended ? "requirement-analysis-lab-quick-option is-recommended" : "requirement-analysis-lab-quick-option"}
            data-testid="requirement-analysis-quick-option"
            key={`${option.key}-${option.label}`}
          >
            <div className="requirement-analysis-lab-quick-option-copy">
              {recommended ? <Tag color="green">推荐</Tag> : null}
              <Text strong>{option.key}</Text>
              <Text>{option.label}</Text>
            </div>
            <Button disabled={disabled} onClick={() => onSelect(option)} size="small">
              选择 {option.key}
            </Button>
          </div>
        );
      })}
    </div>
  );
}

function TurnTab({
  currentTurn,
  onResetSession,
}: {
  currentTurn: RequirementAnalysisTurn | null;
  onResetSession: () => void;
}) {
  const protocolErrors = currentTurn ? validateTurnProtocol(currentTurn) : [];
  return (
    <>
      <div className="requirement-analysis-lab-tab-grid is-turn">
        <section className="requirement-analysis-lab-panel requirement-analysis-lab-turn">
          <PanelHead title="当前 Turn 决策审计" subtitle={currentTurn ? currentTurn.turn_id : "请先进入“会话管理”发送一轮输入。"} />
          {currentTurn ? (
            protocolErrors.length ? (
              <TurnProtocolError missingFields={protocolErrors} onResetSession={onResetSession} turnId={currentTurn.turn_id} />
            ) : (
              <TurnView turn={currentTurn} />
            )
          ) : (
            <Text type="secondary">暂无 Turn。请先进入“会话管理”发送一轮输入。</Text>
          )}
        </section>
      </div>
    </>
  );
}

function TurnProtocolError({
  missingFields,
  onResetSession,
  turnId,
}: {
  missingFields: string[];
  onResetSession: () => void;
  turnId: string;
}) {
  return (
    <Alert
      action={
        <Button onClick={onResetSession} type="primary">
          重新开始验证
        </Button>
      }
      description={
        <div className="requirement-analysis-lab-protocol-error">
          <Text>Turn {turnId} 缺少新版审计协议字段，不能进入当前 Turn 审计视图。</Text>
          <Text type="secondary">{missingFields.join("、")}</Text>
        </div>
      }
      message="当前 Turn 协议错误"
      showIcon
      type="error"
    />
  );
}

function validateTurnProtocol(turn: RequirementAnalysisTurn): string[] {
  const value = turn as unknown as Record<string, unknown>;
  const missing: string[] = [];
  const requiredProperties = [
    "previous_interaction",
    "input_relation",
    "spec_execution",
    "post_update_review",
    "closure_decision",
    "next_interaction",
    "decision_trace",
  ];

  for (const property of requiredProperties) {
    if (!(property in value)) {
      missing.push(property);
    }
  }
  if (!isObject(value.previous_interaction)) {
    missing.push("previous_interaction.prompt");
  }
  if (!isObject(value.input_relation)) {
    missing.push("input_relation.relation");
    missing.push("input_relation.reason");
  }
  if (!isObject(value.spec_execution)) {
    missing.push("spec_execution.interpretation");
    missing.push("spec_execution.document_patch");
  }
  if (!isObject(value.post_update_review)) {
    missing.push("post_update_review.summary");
  }
  if (!isObject(value.closure_decision)) {
    missing.push("closure_decision.status");
    missing.push("closure_decision.reason");
  }
  if (!isObject(value.next_interaction)) {
    missing.push("next_interaction.prompt");
  }
  if (!Array.isArray(value.decision_trace)) {
    missing.push("decision_trace");
  }

  return Array.from(new Set(missing));
}

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function LogTab({ logs }: { logs: RequirementAnalysisProviderLog[] }) {
  const selectedLog = logs[0] ?? null;
  return (
    <>
      <div className="requirement-analysis-lab-tab-grid is-log">
        <section className="requirement-analysis-lab-panel">
          <PanelHead title="Provider 调用日志" subtitle="按调用时间展示 Provider 请求记录。" />
          {logs.length > 0 ? (
            <div className="requirement-analysis-lab-log-list">
              {logs.map((log) => (
                <div className="requirement-analysis-lab-log-item" key={log.call_id}>
                  <Text strong>{log.call_id}</Text>
                  <Text type="secondary">{log.provider_id}</Text>
                  <Tag>{log.status}</Tag>
                </div>
              ))}
            </div>
          ) : (
            <div className="requirement-analysis-lab-empty">
              <Text type="secondary">暂无 Provider 调用日志。</Text>
            </div>
          )}
        </section>
        <section className="requirement-analysis-lab-panel">
          <PanelHead title="调用详情" subtitle={selectedLog ? selectedLog.call_id : "等待 Provider 调用。"} />
          {selectedLog ? (
            <div className="requirement-analysis-lab-detail-list">
              <Text>Provider: {selectedLog.provider_id}</Text>
              <Text>Model: {selectedLog.model}</Text>
              <Text>Status: {selectedLog.status}</Text>
              <Text>Time: {selectedLog.created_at}</Text>
            </div>
          ) : (
            <Text type="secondary">启动会话或发送输入后，这里会显示 Provider 调用细节。</Text>
          )}
        </section>
      </div>
    </>
  );
}

function SessionSummary({ session }: { session: RequirementAnalysisSession | null }) {
  return (
    <section className="requirement-analysis-lab-panel requirement-analysis-lab-summary">
      <PanelHead title="会话摘要 / 过程产物" subtitle="主视角是需求规格完成度树；沟通路径只记录用户输入产生的影响。" />
      {session ? (
        <SpecCompletionTree session={session} />
      ) : (
        <div className="requirement-analysis-lab-empty">
          <Text type="secondary">尚未创建会话，暂无摘要。</Text>
        </div>
      )}
    </section>
  );
}

function SpecCompletionTree({ session }: { session: RequirementAnalysisSession }) {
  return (
    <div className="requirement-analysis-lab-spec-summary">
      <div className="requirement-analysis-lab-summary-title-row">
        <Text strong>需求规格完成度树</Text>
        <Tag color="blue">focus: {session.active_spec_node_id ?? "已完成"}</Tag>
      </div>
      <div className="requirement-analysis-lab-spec-tree" role="tree">
        {session.spec_tree.map((node) => (
          <SpecTreeNode key={node.node_id} node={node} />
        ))}
      </div>
      <div className="requirement-analysis-lab-turn-path-panel">
        <Text strong>沟通路径</Text>
        {session.turn_path.length > 0 ? (
          <div className="requirement-analysis-lab-turn-path-list">
            {session.turn_path.map((item) => (
              <div className="requirement-analysis-lab-turn-path-item" key={item.turn_id}>
                <Text strong>{item.turn_id}</Text>
                <Text type="secondary">{item.affected_node_ids?.join("、") || item.node_id}</Text>
                <Text>{item.answer_summary || "等待回答摘要"}</Text>
              </div>
            ))}
          </div>
        ) : (
          <Text type="secondary">尚未产生沟通路径。用户输入后会记录影响到的规格节点。</Text>
        )}
      </div>
    </div>
  );
}

function SpecTreeNode({ node, depth = 0 }: { node: RequirementAnalysisSpecTreeNode; depth?: number }) {
  const isLeaf = node.children.length === 0;
  return (
    <div className="requirement-analysis-lab-spec-node" role="treeitem" aria-expanded={!isLeaf ? true : undefined}>
      <div className={`requirement-analysis-lab-spec-row is-${node.status}`} style={{ paddingLeft: `${depth * 18 + 8}px` }}>
        <span className={`requirement-analysis-lab-spec-marker is-${node.status}`}>{formatSpecStatusMarker(node.status)}</span>
        <Text strong className="requirement-analysis-lab-spec-title" title={node.title}>
          {node.title}
        </Text>
        <Text type="secondary" className="requirement-analysis-lab-spec-section">
          {node.target_section}
        </Text>
        <Tag>{formatSpecStatus(node.status)}</Tag>
      </div>
      {node.children.map((child) => (
        <SpecTreeNode depth={depth + 1} key={child.node_id} node={child} />
      ))}
    </div>
  );
}

function formatSpecStatus(status: string) {
  const labels: Record<string, string> = {
    open: "待确认",
    partial: "部分完成",
    closed: "已关闭",
    skipped: "已跳过",
  };
  return labels[status] ?? status;
}

function formatSpecStatusMarker(status: string) {
  if (status === "closed") {
    return "✓";
  }
  if (status === "partial") {
    return "…";
  }
  if (status === "skipped") {
    return "x";
  }
  return "?";
}

function formatRelationLabel(relation: string) {
  const labels: Record<string, string> = {
    none: "无上轮留题",
    answered: "回答留题",
    selected_option: "选择选项",
    partially_answered: "部分回答",
    topic_shift: "主动改题",
    challenge: "反驳修正",
    supplement: "补充说明",
    unrelated: "无关输入",
    unknown: "未知",
  };
  return labels[relation] ?? relation;
}

function formatRelationColor(relation: string) {
  if (relation === "answered" || relation === "selected_option" || relation === "supplement") {
    return "green";
  }
  if (relation === "challenge" || relation === "topic_shift") {
    return "gold";
  }
  if (relation === "unknown") {
    return "default";
  }
  return "blue";
}

function formatInteractionType(type: string) {
  const labels: Record<string, string> = {
    none: "无留题",
    open_question: "开放问题",
    choice_question: "选择题",
    suggestion: "建议方向",
    free_continue: "自由补充",
  };
  return labels[type] ?? type;
}

function formatClosureStatus(status: string) {
  const labels: Record<string, string> = {
    closed: "本轮已闭环",
    needs_followup: "需要继续追问",
    open: "仍在处理",
  };
  return labels[status] ?? status;
}

function PanelHead({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="requirement-analysis-lab-panel-head">
      <Title level={4}>{title}</Title>
      <Text type="secondary">{subtitle}</Text>
    </div>
  );
}

function TurnView({ turn }: { turn: RequirementAnalysisTurn }) {
  return (
    <div className="requirement-analysis-lab-turn-view">
      <div className="requirement-analysis-lab-turn-card is-audit">
        <Text type="secondary">上轮系统留题</Text>
        <div className="requirement-analysis-lab-turn-inline">
          <Tag>{formatInteractionType(turn.previous_interaction.type)}</Tag>
          {turn.previous_interaction.target_spec_node_ids.map((nodeId) => (
            <Tag key={nodeId}>{nodeId}</Tag>
          ))}
        </div>
        <Text strong>{turn.previous_interaction.prompt || "无，用户自由发起。"}</Text>
        {turn.previous_interaction.reason ? <Text type="secondary">{turn.previous_interaction.reason}</Text> : null}
        {turn.previous_interaction.options.length ? <OptionSummary options={turn.previous_interaction.options} /> : null}
      </div>
      <div className="requirement-analysis-lab-turn-card is-audit">
        <Text type="secondary">本轮用户输入</Text>
        <Text>{turn.user_input}</Text>
        <div className="requirement-analysis-lab-turn-inline">
          <Tag>{turn.normalized_input.input_type}</Tag>
          {turn.normalized_input.matched_option ? <Tag>选项 {turn.normalized_input.matched_option}</Tag> : null}
        </div>
        {turn.normalized_input.matched_option_label ? (
          <Text type="secondary">匹配选项：{turn.normalized_input.matched_option_label}</Text>
        ) : null}
      </div>
      <div className="requirement-analysis-lab-turn-card is-audit">
        <Text type="secondary">输入承接判断</Text>
        <Tag color={formatRelationColor(turn.input_relation.relation)}>
          {formatRelationLabel(turn.input_relation.relation)}
        </Tag>
        <Text>{turn.input_relation.reason}</Text>
      </div>
      <div className="requirement-analysis-lab-turn-card">
        <Text type="secondary">规格补充执行</Text>
        <Text strong>{turn.spec_execution.interpretation.summary}</Text>
        <Text>{turn.spec_execution.assistant_message}</Text>
        <Text strong>确认事实</Text>
        {turn.spec_execution.confirmed_facts.map((fact) => (
          <Text key={fact}>{fact}</Text>
        ))}
        <Text strong>影响节点</Text>
        {turn.spec_execution.affected_spec_nodes.map((node) => (
          <div className="requirement-analysis-lab-affected-node" key={`${node.node_id}-${node.target_section}`}>
            <Text strong>{node.node_id ?? "未绑定节点"}</Text>
            <Text>{node.target_section ?? node.title ?? "未绑定章节"}</Text>
            <Text type="secondary">{node.reason}</Text>
          </div>
        ))}
        <Text strong>正文建议</Text>
        {turn.spec_execution.document_patch.map((patch) => (
          <div className="requirement-analysis-lab-patch" key={`${patch.section}-${patch.operation}`}>
            <Text strong>{patch.section}</Text>
            <Text>{patch.content}</Text>
          </div>
        ))}
        <StateChangeSummary stateChanges={turn.spec_execution.state_changes} />
      </div>
      <div className="requirement-analysis-lab-turn-card">
        <Text type="secondary">补充后状态回看</Text>
        <Text strong>{turn.post_update_review.summary}</Text>
        <div className="requirement-analysis-lab-turn-inline">
          <Tag color={turn.post_update_review.previous_interaction_resolved ? "green" : "gold"}>
            {turn.post_update_review.previous_interaction_resolved ? "上轮留题已处理" : "上轮留题未完全处理"}
          </Tag>
          <Tag color={turn.post_update_review.current_spec_node_sufficient ? "green" : "gold"}>
            {turn.post_update_review.current_spec_node_sufficient ? "当前节点足够" : "当前节点仍不足"}
          </Tag>
          <Tag color={turn.post_update_review.needs_followup_on_same_topic ? "gold" : "green"}>
            {turn.post_update_review.needs_followup_on_same_topic ? "同题继续追问" : "可进入下一步"}
          </Tag>
        </div>
        {turn.post_update_review.remaining_gaps.length ? (
          <>
            <Text strong>剩余缺口</Text>
            {turn.post_update_review.remaining_gaps.map((gap) => (
              <Text key={gap}>{gap}</Text>
            ))}
          </>
        ) : null}
      </div>
      <div className="requirement-analysis-lab-turn-card">
        <Text type="secondary">本轮处理闭环</Text>
        <Tag color={turn.closure_decision.status === "closed" ? "green" : "gold"}>
          {formatClosureStatus(turn.closure_decision.status)}
        </Tag>
        <Text>{turn.closure_decision.reason}</Text>
        <Text type="secondary">下一步策略：{turn.closure_decision.next_action}</Text>
      </div>
      <div className="requirement-analysis-lab-turn-card">
        <Text type="secondary">下一轮交互设计</Text>
        <div className="requirement-analysis-lab-turn-inline">
          <Tag>{formatInteractionType(turn.next_interaction.type)}</Tag>
          {turn.next_interaction.target_spec_node_ids.map((nodeId) => (
            <Tag key={nodeId}>{nodeId}</Tag>
          ))}
        </div>
        <Text strong>{turn.next_interaction.prompt || "无，等待用户自由输入。"}</Text>
        {turn.next_interaction.reason ? <Text type="secondary">{turn.next_interaction.reason}</Text> : null}
        {turn.next_interaction.options.length ? <OptionSummary options={turn.next_interaction.options} /> : null}
      </div>
      <div className="requirement-analysis-lab-turn-card">
        <Text type="secondary">决策依据</Text>
        <ol>
          {turn.decision_trace.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function OptionSummary({ options }: { options: RequirementAnalysisQuickOption[] }) {
  return (
    <div className="requirement-analysis-lab-turn-options">
      {options.map((option) => (
        <div className="requirement-analysis-lab-turn-option" key={option.key}>
          <Text strong>{option.key}</Text>
          <Text>{option.label}</Text>
          {option.recommended ? <Tag color="green">推荐</Tag> : null}
        </div>
      ))}
    </div>
  );
}

function StateChangeSummary({ stateChanges }: { stateChanges: RequirementAnalysisTurn["spec_execution"]["state_changes"] }) {
  return (
    <div className="requirement-analysis-lab-state-changes">
      <Text strong>状态变化</Text>
      <Text>关闭问题：{stateChanges.closed_question_ids.length ? stateChanges.closed_question_ids.join("、") : "无"}</Text>
      <Text>新增问题：{stateChanges.created_question_ids.length ? stateChanges.created_question_ids.join("、") : "无"}</Text>
      <Text>关闭节点：{stateChanges.closed_spec_node_ids.length ? stateChanges.closed_spec_node_ids.join("、") : "无"}</Text>
      <Text>下一焦点：{stateChanges.next_active_spec_node_id ?? "无"}</Text>
    </div>
  );
}

function ContractGrid({ stableContract }: { stableContract: Record<string, boolean> }) {
  const labels: Record<string, string> = {
    formal_document: "正式需求规格文档",
    template_object: "模板对象",
    knowledge_binding: "知识绑定",
    draft_persistence: "草稿持久化",
    check_and_freeze: "检查与冻结",
    p2_to_p3_output: "P2 -> P3 输出",
  };

  return (
    <div className="requirement-analysis-lab-contract-grid">
      {Object.entries(labels).map(([key, label]) => (
        <div className="requirement-analysis-lab-contract-item" key={key}>
          <Text strong>{label}</Text>
          <Tag color={stableContract[key] ? "green" : "red"}>{stableContract[key] ? "stable" : "missing"}</Tag>
        </div>
      ))}
    </div>
  );
}

function formatWritePolicy(policy: string) {
  if (policy === "patch_suggestion_only") {
    return "只生成 document_patch 建议";
  }
  return policy;
}

function formatProviderStatus(status: string) {
  if (status === "active") {
    return "已启用";
  }
  if (status === "not_configured") {
    return "未配置";
  }
  return status;
}

function formatQuickOptionInput(option: RequirementAnalysisQuickOption) {
  return `${option.key}，${option.label}`;
}

function resolveDefaultProviderId(providers: RequirementAnalysisProvider[]) {
  return (
    providers.find((provider) => provider.status === "active" && provider.provider_id !== "mock")?.provider_id ??
    providers[0]?.provider_id ??
    "mock"
  );
}
