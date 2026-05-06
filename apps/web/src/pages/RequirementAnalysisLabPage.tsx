import { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Button, Input, Space, Spin, Tabs, Tag, Typography } from "antd";
import assistantAvatar from "../components/requirementAnalysisAssistantAvatar.svg";
import userAvatar from "../components/requirementAnalysisUserAvatar.svg";

import type {
  RequirementAnalysisOrchestrator,
  RequirementAnalysisOrchestratorEnvelope,
  RequirementAnalysisFieldSchema,
  RequirementAnalysisLabConfig,
  RequirementAnalysisProviderLog,
  RequirementAnalysisProvider,
  RequirementAnalysisTemplateDetail,
  RequirementAnalysisTemplateSummary,
  RequirementAnalysisQuickOption,
  RequirementAnalysisSession,
  RequirementAnalysisSpecTreeNode,
  RequirementAnalysisTurn,
  RequirementAnalysisTurnStageAudit,
} from "../lib/api";
import {
  createRequirementAnalysisSession,
  createRequirementAnalysisTurn,
  getRequirementAnalysisTemplate,
  saveRequirementAnalysisTemplate,
} from "../lib/requirementAnalysis";
import {
  getRequirementAnalysisProviderLogFieldNote,
  resolveDefaultRequirementAnalysisOrchestratorId,
  resolveDefaultRequirementAnalysisProviderId,
  buildRequirementAnalysisWorkingDocumentViewModel,
  resolveRequirementAnalysisWritePolicyLabel,
  validateRequirementAnalysisTurnProtocol,
} from "../lib/requirementAnalysisLabViewModel";
import { useRequirementAnalysisLabBootstrap } from "../lib/useRequirementAnalysisLabBootstrap";
import "./RequirementAnalysisLabPage.css";

const { Text, Title } = Typography;
const { TextArea } = Input;

type RequirementAnalysisLabTab = "config" | "session" | "turn" | "log";
type WorkingDocumentFragment = RequirementAnalysisSession["working_document"]["revision_fragments"][number];

function formatRequirementAnalysisTurnLabel(turnId: string) {
  const match = turnId.match(/(\d+)$/);
  if (!match) {
    return "本轮修订";
  }
  return `第${Number(match[1])}轮修订`;
}

function formatRequirementAnalysisMessageRole(role: string) {
  if (role === "assistant") {
    return "助手";
  }
  if (role === "user") {
    return "用户";
  }
  return role;
}

export function RequirementAnalysisLabPage() {
  const { labConfig, orchestratorsEnvelope, providers, templates, loading, error: bootstrapError } = useRequirementAnalysisLabBootstrap();
  const [selectedOrchestratorId, setSelectedOrchestratorId] = useState("");
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [templateDetail, setTemplateDetail] = useState<RequirementAnalysisTemplateDetail | null>(null);
  const [templateDraft, setTemplateDraft] = useState("");
  const [templateLoading, setTemplateLoading] = useState(false);
  const [templateSaving, setTemplateSaving] = useState(false);
  const [topic, setTopic] = useState("");
  const [activeTab, setActiveTab] = useState<RequirementAnalysisLabTab>("config");
  const [session, setSession] = useState<RequirementAnalysisSession | null>(null);
  const [currentTurn, setCurrentTurn] = useState<RequirementAnalysisTurn | null>(null);
  const [userInput, setUserInput] = useState("");
  const [pendingUserInput, setPendingUserInput] = useState<string | null>(null);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!labConfig || !orchestratorsEnvelope) {
      return;
    }
    setTopic((current) => current || labConfig.defaults.topic);
    setSelectedOrchestratorId((current) =>
      current || resolveDefaultRequirementAnalysisOrchestratorId(orchestratorsEnvelope.items, labConfig.defaults.orchestrator_id),
    );
    setSelectedProviderId((current) =>
      current || resolveDefaultRequirementAnalysisProviderId(providers, labConfig.defaults.provider_id),
    );
    setSelectedTemplateId((current) => {
      if (current) {
        return current;
      }
      const configuredTemplateId = labConfig.defaults.template_id;
      if (templates.some((template) => template.template_id === configuredTemplateId)) {
        return configuredTemplateId;
      }
      return templates[0]?.template_id ?? configuredTemplateId;
    });
  }, [labConfig, orchestratorsEnvelope, providers, templates]);

  useEffect(() => {
    if (!selectedTemplateId) {
      return;
    }
    let cancelled = false;
    async function loadTemplate() {
      try {
        setTemplateLoading(true);
        const response = await getRequirementAnalysisTemplate(selectedTemplateId);
        if (cancelled) {
          return;
        }
        setTemplateDetail(response.data);
        setTemplateDraft(response.data.content);
      } catch (templateError) {
        if (!cancelled) {
          setError(templateError instanceof Error ? templateError.message : "加载需求规格说明模板失败");
        }
      } finally {
        if (!cancelled) {
          setTemplateLoading(false);
        }
      }
    }
    void loadTemplate();
    return () => {
      cancelled = true;
    };
  }, [selectedTemplateId]);

  const selectedOrchestrator = useMemo(
    () => orchestratorsEnvelope?.items.find((item) => item.orchestrator_id === selectedOrchestratorId) ?? null,
    [orchestratorsEnvelope, selectedOrchestratorId],
  );

  const activeProvider = useMemo(
    () => providers.find((provider) => provider.provider_id === selectedProviderId) ?? null,
    [providers, selectedProviderId],
  );
  const providerOptions = useMemo(() => sortRequirementAnalysisProviders(providers), [providers]);

  const logCount = session?.provider_logs.length ?? 0;
  const defaultWritePolicyLabel = labConfig
    ? resolveRequirementAnalysisWritePolicyLabel(labConfig.defaults.write_policy, labConfig.write_policies)
    : "写入策略加载中";
  const effectiveError = error ?? bootstrapError;

  async function handleStart() {
    setActiveTab("session");
    try {
      setActing(true);
      const response = await createRequirementAnalysisSession({
        topic,
        orchestrator_id: selectedOrchestratorId,
        provider_id: selectedProviderId,
        model: labConfig?.defaults.model ?? "",
        template_id: selectedTemplateId || labConfig?.defaults.template_id,
        knowledge_package_id: labConfig?.defaults.knowledge_package_id,
        write_policy: labConfig?.defaults.write_policy,
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

  async function handleSaveTemplate() {
    if (!selectedTemplateId) {
      return;
    }
    try {
      setTemplateSaving(true);
      const response = await saveRequirementAnalysisTemplate(selectedTemplateId, templateDraft);
      setTemplateDetail(response.data);
      setTemplateDraft(response.data.content);
      setError(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "保存需求规格说明模板失败");
    } finally {
      setTemplateSaving(false);
    }
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
              <Title level={2}>{labConfig?.page.title ?? "加载 Lab 配置中"}</Title>
              <Text type="secondary">{labConfig?.page.subtitle ?? "加载 Lab 配置中..."}</Text>
          </div>
        </div>
        <Space wrap>
          <Tag color="blue">独立路由</Tag>
          <Tag color="green">可插拔组织器</Tag>
          <Tag color="orange">{defaultWritePolicyLabel}</Tag>
        </Space>
      </header>

      {effectiveError ? <Alert type="error" showIcon message={effectiveError} /> : null}

      {loading ? (
        <section className="requirement-analysis-lab-loading">
          <Spin />
        </section>
      ) : orchestratorsEnvelope && labConfig ? (
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
              subtitle="Model / Runner Calls"
              title="调用日志"
            />
          </aside>

          <section className="requirement-analysis-lab-workspace">
            {activeTab === "config" ? (
              <ConfigTab
                activeProvider={activeProvider}
                acting={acting}
                labConfig={labConfig}
                currentSession={session}
                onEnterSession={() => setActiveTab("session")}
                onProviderSelect={setSelectedProviderId}
                onStart={() => void handleStart()}
                onOrchestratorSelect={setSelectedOrchestratorId}
                onTopicChange={setTopic}
                orchestratorsEnvelope={orchestratorsEnvelope}
                providers={providerOptions}
                templates={templates}
                selectedTemplateId={selectedTemplateId}
                onTemplateSelect={setSelectedTemplateId}
                templateDetail={templateDetail}
                templateDraft={templateDraft}
                onTemplateDraftChange={setTemplateDraft}
                onSaveTemplate={() => void handleSaveTemplate()}
                templateLoading={templateLoading}
                templateSaving={templateSaving}
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
                writePolicies={labConfig.write_policies}
              />
            ) : null}
            {activeTab === "turn" ? <TurnTab currentTurn={currentTurn} labConfig={labConfig} onResetSession={handleResetSession} /> : null}
            {activeTab === "log" ? <LogTab logSchema={labConfig.provider_log_schema} logs={session?.provider_logs ?? []} /> : null}
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
  labConfig,
  currentSession,
  onEnterSession,
  onProviderSelect,
  onStart,
  onOrchestratorSelect,
  onTopicChange,
  onTemplateDraftChange,
  onTemplateSelect,
  onSaveTemplate,
  orchestratorsEnvelope,
  providers,
  templates,
  selectedTemplateId,
  templateDetail,
  templateDraft,
  templateLoading,
  templateSaving,
  selectedOrchestrator,
  selectedOrchestratorId,
  selectedProviderId,
  topic,
}: {
  activeProvider: RequirementAnalysisProvider | null;
  acting: boolean;
  labConfig: RequirementAnalysisLabConfig;
  currentSession: RequirementAnalysisSession | null;
  onEnterSession: () => void;
  onProviderSelect: (providerId: string) => void;
  onStart: () => void;
  onOrchestratorSelect: (orchestratorId: string) => void;
  onTopicChange: (topic: string) => void;
  onTemplateDraftChange: (content: string) => void;
  onTemplateSelect: (templateId: string) => void;
  onSaveTemplate: () => void;
  orchestratorsEnvelope: RequirementAnalysisOrchestratorEnvelope;
  providers: RequirementAnalysisProvider[];
  templates: RequirementAnalysisTemplateSummary[];
  selectedTemplateId: string;
  templateDetail: RequirementAnalysisTemplateDetail | null;
  templateDraft: string;
  templateLoading: boolean;
  templateSaving: boolean;
  selectedOrchestrator: RequirementAnalysisOrchestrator | null;
  selectedOrchestratorId: string;
  selectedProviderId: string;
  topic: string;
}) {
  const topicField = labConfig.startup_fields.find((field) => field.field === "topic");
  const templateDirty = Boolean(templateDetail && templateDraft !== templateDetail.content);
  return (
    <>
      <div className="requirement-analysis-lab-tab-grid is-config">
        <div className="requirement-analysis-lab-config-stack">
          <section className="requirement-analysis-lab-panel requirement-analysis-lab-orchestrators">
            <PanelHead title="可替换组织器" subtitle="选择本轮需求规格探索使用的组织器策略。" />
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
              <Input
                placeholder={topicField?.placeholder}
                value={topic}
                onChange={(event) => onTopicChange(event.target.value)}
              />
            </label>
            <div className="requirement-analysis-lab-provider-row">
              {providers.map((provider) => (
                <button
                  className={
                    provider.provider_id === selectedProviderId
                      ? "requirement-analysis-lab-provider is-selected"
                      : "requirement-analysis-lab-provider"
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
              {selectedOrchestrator?.name ?? selectedOrchestratorId}；当前模板：{templateDetail?.name ?? selectedTemplateId}
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
        </div>

        <section className="requirement-analysis-lab-panel requirement-analysis-lab-template-panel">
          <PanelHead title="需求规格说明模板" subtitle="选择并编辑本次组织器 Lab 使用的 Markdown 模板。" />
          <div className="requirement-analysis-lab-template-layout">
            <div className="requirement-analysis-lab-template-list">
              {templates.length ? (
                templates.map((template) => (
                  <button
                    className={
                      template.template_id === selectedTemplateId
                        ? "requirement-analysis-lab-template-option is-selected"
                        : "requirement-analysis-lab-template-option"
                    }
                    key={template.template_id}
                    onClick={() => onTemplateSelect(template.template_id)}
                    type="button"
                  >
                    <span>
                      <Text strong>{template.name}</Text>
                      <Text type="secondary">{template.template_id}</Text>
                    </span>
                    <Tag color={template.status === "active" ? "green" : "default"}>{template.status}</Tag>
                  </button>
                ))
              ) : (
                <div className="requirement-analysis-lab-empty">
                  <Text type="secondary">暂无可编辑模板。</Text>
                </div>
              )}
            </div>
            <Spin spinning={templateLoading}>
              <div className="requirement-analysis-lab-template-editor">
                <div className="requirement-analysis-lab-template-meta">
                  <Text strong>{templateDetail?.name ?? "未选择模板"}</Text>
                  <Text type="secondary">{templateDetail?.description ?? "选择左侧模板后可查看并编辑其 Markdown 正文。"}</Text>
                </div>
                <Space className="requirement-analysis-lab-template-actions" wrap>
                  <Tag color={templateDirty ? "orange" : "green"}>{templateDirty ? "未保存" : "已同步"}</Tag>
                  {templateDetail?.format ? <Tag>{templateDetail.format}</Tag> : null}
                  <Button
                    disabled={!selectedTemplateId || templateLoading}
                    loading={templateSaving}
                    onClick={onSaveTemplate}
                    type="primary"
                  >
                    保存模板
                  </Button>
                </Space>
                <TextArea
                  aria-label="需求规格说明模板正文"
                  autoSize={false}
                  className="requirement-analysis-lab-template-textarea"
                  disabled={!selectedTemplateId}
                  onChange={(event) => onTemplateDraftChange(event.target.value)}
                  placeholder="选择模板后，这里会显示对应的 Markdown 正文。"
                  value={templateDraft}
                />
              </div>
            </Spin>
          </div>
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
  writePolicies,
}: {
  acting: boolean;
  currentTurn: RequirementAnalysisTurn | null;
  onQuickOptionSelect: (option: RequirementAnalysisQuickOption) => void;
  onSend: () => void;
  pendingUserInput: string | null;
  session: RequirementAnalysisSession | null;
  setUserInput: (value: string) => void;
  userInput: string;
  writePolicies: RequirementAnalysisLabConfig["write_policies"];
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
                <Tag>{resolveRequirementAnalysisWritePolicyLabel(session.write_policy, writePolicies)}</Tag>
                <Tag>{session.topic}</Tag>
              </div>
              <div className="requirement-analysis-lab-message-list" ref={messageListRef}>
                {session.messages.map((message) => (
                  <div
                    className={`requirement-analysis-lab-message is-${message.role}`}
                    data-testid={`requirement-analysis-message-${message.role}`}
                    key={message.id}
                  >
                    <div className="requirement-analysis-lab-message-meta">
                      <img
                        alt={message.role === "assistant" ? "助手头像" : "用户头像"}
                        className="requirement-analysis-lab-message-avatar"
                        src={message.role === "assistant" ? assistantAvatar : userAvatar}
                      />
                      <span>{formatRequirementAnalysisMessageRole(message.role)}</span>
                    </div>
                    <p>{message.content}</p>
                  </div>
                ))}
                {pendingUserInput ? (
                  <>
                    <div className="requirement-analysis-lab-message is-user is-pending" data-testid="requirement-analysis-message-user-pending">
                      <div className="requirement-analysis-lab-message-meta">
                        <img alt="用户头像" className="requirement-analysis-lab-message-avatar" src={userAvatar} />
                        <span>{formatRequirementAnalysisMessageRole("user")}</span>
                      </div>
                      <p>{pendingUserInput}</p>
                    </div>
                    <div
                      className="requirement-analysis-lab-message is-assistant is-pending"
                      data-testid="requirement-analysis-message-assistant-pending"
                    >
                      <div className="requirement-analysis-lab-message-meta">
                        <img alt="助手头像" className="requirement-analysis-lab-message-avatar" src={assistantAvatar} />
                        <span>{formatRequirementAnalysisMessageRole("assistant")}</span>
                      </div>
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
  labConfig,
  onResetSession,
}: {
  currentTurn: RequirementAnalysisTurn | null;
  labConfig: RequirementAnalysisLabConfig;
  onResetSession: () => void;
}) {
  const protocolErrors = currentTurn ? validateRequirementAnalysisTurnProtocol(currentTurn, labConfig.turn_audit_schema.required_fields) : [];
  return (
    <>
      <div className="requirement-analysis-lab-tab-grid is-turn-single" data-testid="requirement-analysis-turn-grid">
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

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function LogTab({ logSchema, logs }: { logSchema: RequirementAnalysisFieldSchema; logs: RequirementAnalysisProviderLog[] }) {
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
  const selectedLog =
    logs.find((log) => log.call_id === selectedCallId) ?? logs[0] ?? null;

  useEffect(() => {
    if (!selectedLog) {
      setSelectedCallId(null);
      return;
    }
    if (!logs.some((log) => log.call_id === selectedCallId)) {
      setSelectedCallId(selectedLog.call_id);
    }
  }, [logs, selectedCallId, selectedLog]);

  return (
    <>
      <div className="requirement-analysis-lab-tab-grid is-log">
        <section className="requirement-analysis-lab-panel">
          <PanelHead title="模型 / Runner 调用日志" subtitle="只展示外部模型 Provider 或本地 Runner 调用；服务端内部阶段审计在当前 Turn 中查看。" />
          {logs.length > 0 ? (
            <div className="requirement-analysis-lab-log-list">
              {logs.map((log) => (
                <button
                  className={`requirement-analysis-lab-log-item ${selectedLog?.call_id === log.call_id ? "is-selected" : ""}`}
                  key={log.call_id}
                  onClick={() => setSelectedCallId(log.call_id)}
                  type="button"
                >
                  <span className="requirement-analysis-lab-log-main">
                    <Text strong>{log.call_id}</Text>
                    <Text type="secondary">
                      {log.turn_id ?? "未绑定 Turn"} · {formatStageLabel(log.stage_id, log.stage_type, getLogPromptId(log))}
                    </Text>
                  </span>
                  <Text type="secondary">{log.provider_id}</Text>
                  <span className="requirement-analysis-lab-log-tags">
                    {log.stage_id ? <Tag color={log.stage_id === "review" ? "purple" : "blue"}>{log.stage_id}</Tag> : null}
                    <Tag>{log.status}</Tag>
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <div className="requirement-analysis-lab-empty">
              <Text type="secondary">暂无模型或 Runner 调用日志。</Text>
            </div>
          )}
        </section>
        <section className="requirement-analysis-lab-panel">
          <PanelHead title="调用详情" subtitle={selectedLog ? selectedLog.call_id : "等待模型或 Runner 调用。"} />
          {selectedLog ? (
            <ProviderLogDetail log={selectedLog} logSchema={logSchema} />
          ) : (
            <Text type="secondary">启动会话或发送输入后，这里会显示模型或 Runner 调用细节。</Text>
          )}
        </section>
      </div>
    </>
  );
}

function ProviderLogDetail({ log, logSchema }: { log: RequirementAnalysisProviderLog; logSchema: RequirementAnalysisFieldSchema }) {
  const audit = log.audit ?? {};
  const promptBundle = getRecord(audit.provider_request, "prompt_bundle");
  const requestMessages = getArray(audit.provider_request, "messages");
  const mockContext = getRecord(audit.provider_request, "mock_context");
  const runnerContext = getRecord(audit.provider_request, "runner_context");
  const rawContent = getString(audit.provider_response, "raw_content");
  const parsedProviderOutput = getRecord(audit.provider_response, "parsed_json");

  return (
    <Tabs
      className="requirement-analysis-lab-log-detail-tabs"
      items={[
        {
          key: "overview",
          label: "概览",
          children: (
            <div className="requirement-analysis-lab-detail-list">
              <div className="requirement-analysis-lab-log-meta">
                <Text>Provider: {log.provider_id}</Text>
                <Text>Model: {log.model}</Text>
                <Text>Status: {log.status}</Text>
                <Text>Turn: {log.turn_id ?? "未绑定 Turn"}</Text>
                <Text>Stage: {formatStageLabel(log.stage_id, log.stage_type, getLogPromptId(log))}</Text>
                <Text>Orchestrator: {log.orchestrator_id ?? "未记录"}</Text>
                <Text>Mode: {log.orchestrator_mode ?? "未记录"}</Text>
                <Text>Time: {log.created_at}</Text>
              </div>
              <LogAuditBlock logSchema={logSchema} title="user_input" value={audit.user_input ?? ""} />
              <LogAuditBlock logSchema={logSchema} title="normalized_input" value={audit.normalized_input ?? {}} />
            </div>
          ),
        },
        {
          key: "context",
          label: "当前 turn 上下文",
          children: (
            <div className="requirement-analysis-lab-detail-list">
              <LogAuditBlock logSchema={logSchema} title="provider_request.prompt_bundle.context_json" value={getString(promptBundle, "context_json")} />
              <LogAuditBlock logSchema={logSchema} title="provider_request.prompt_bundle.stage_id" value={getString(promptBundle, "stage_id") || log.stage_id || getString(mockContext, "stage_id")} />
              <LogAuditBlock logSchema={logSchema} title="provider_request.prompt_bundle.prompt_id" value={getString(promptBundle, "prompt_id") || getLogPromptId(log)} />
              <LogAuditBlock
                logSchema={logSchema}
                title="provider_request.prompt_bundle.working_document_json"
                value={getString(promptBundle, "working_document_json")}
              />
              <LogAuditBlock
                logSchema={logSchema}
                title="provider_request.prompt_bundle.working_document_after_apply_json"
                value={getString(promptBundle, "working_document_after_apply_json")}
              />
              <LogAuditBlock
                logSchema={logSchema}
                title="provider_request.prompt_bundle.working_document_excerpt"
                value={getString(promptBundle, "working_document_excerpt")}
              />
              <LogAuditBlock logSchema={logSchema} title="provider_request.prompt_bundle.review_target_paths" value={getArray(promptBundle, "review_target_paths")} />
              <LogAuditBlock logSchema={logSchema} title="provider_request.prompt_bundle.recent_revision_fragments" value={getArray(promptBundle, "recent_revision_fragments")} />
              <LogAuditBlock logSchema={logSchema} title="provider_request.mock_context" value={mockContext} />
              <LogAuditBlock logSchema={logSchema} title="provider_request.runner_context" value={runnerContext} />
            </div>
          ),
        },
        {
          key: "output-format",
          label: "输出格式要求",
          children: (
            <div className="requirement-analysis-lab-detail-list">
              <LogAuditBlock logSchema={logSchema} title="provider_request.prompt_bundle.schema_json" value={getString(promptBundle, "schema_json")} />
            </div>
          ),
        },
        {
          key: "request",
          label: "请求",
          children: (
            <div className="requirement-analysis-lab-detail-list">
              <LogAuditBlock logSchema={logSchema} title="provider_request.messages" value={requestMessages} />
              <LogAuditBlock
                logSchema={logSchema}
                title="provider_request.prompt_bundle.assembled_prompt"
                value={getString(promptBundle, "assembled_prompt")}
              />
              <LogAuditBlock logSchema={logSchema} title="provider_request.prompt_bundle.stage_id" value={getString(promptBundle, "stage_id") || log.stage_id || getString(mockContext, "stage_id")} />
              <LogAuditBlock logSchema={logSchema} title="provider_request.prompt_bundle.prompt_id" value={getString(promptBundle, "prompt_id") || getLogPromptId(log)} />
              <LogAuditBlock
                logSchema={logSchema}
                title="provider_request.prompt_bundle.working_document_json"
                value={getString(promptBundle, "working_document_json")}
              />
              <LogAuditBlock
                logSchema={logSchema}
                title="provider_request.prompt_bundle.working_document_after_apply_json"
                value={getString(promptBundle, "working_document_after_apply_json")}
              />
              <LogAuditBlock
                logSchema={logSchema}
                title="provider_request.prompt_bundle.working_document_excerpt"
                value={getString(promptBundle, "working_document_excerpt")}
              />
              <LogAuditBlock logSchema={logSchema} title="provider_request.prompt_bundle.review_target_paths" value={getArray(promptBundle, "review_target_paths")} />
              <LogAuditBlock logSchema={logSchema} title="provider_request.prompt_bundle.recent_revision_fragments" value={getArray(promptBundle, "recent_revision_fragments")} />
              <LogAuditBlock logSchema={logSchema} title="provider_request.prompt_bundle.review_goal" value={getString(promptBundle, "review_goal")} />
              <LogAuditBlock logSchema={logSchema} title="provider_request.mock_context" value={mockContext} />
              <LogAuditBlock logSchema={logSchema} title="provider_request.runner_context" value={runnerContext} />
            </div>
          ),
        },
        {
          key: "raw",
          label: "原始输出",
          children: (
            <div className="requirement-analysis-lab-detail-list">
              <LogAuditBlock logSchema={logSchema} title="provider_response.raw_content" value={rawContent} />
              <LogAuditBlock logSchema={logSchema} title="provider_response.parsed_json" value={parsedProviderOutput} />
              <LogAuditBlock logSchema={logSchema} title="provider_response.target_review_json" value={getRecord(audit.provider_response, "target_review_json")} />
              <LogAuditBlock logSchema={logSchema} title="provider_response.global_review_json" value={getRecord(audit.provider_response, "global_review_json")} />
            </div>
          ),
        },
        {
          key: "postprocess",
          label: "输出后处理",
          children: (
            <div className="requirement-analysis-lab-detail-list">
              <LogAuditBlock logSchema={logSchema} title="provider_normalized_output" value={audit.provider_normalized_output ?? {}} />
              <LogAuditBlock logSchema={logSchema} title="service_output" value={audit.service_output ?? {}} />
            </div>
          ),
        },
      ]}
    />
  );
}

function LogAuditBlock({ logSchema, title, value }: { logSchema: RequirementAnalysisFieldSchema; title: string; value: unknown }) {
  const note = getRequirementAnalysisProviderLogFieldNote(logSchema, title);
  return (
    <div className="requirement-analysis-lab-log-audit-block">
      <div className="requirement-analysis-lab-log-audit-title">
        <Text strong>{title}</Text>
        {note ? <Text type="secondary">（{note}）</Text> : null}
      </div>
      <pre>{formatAuditValue(value)}</pre>
    </div>
  );
}

function formatAuditValue(value: unknown): string {
  if (typeof value === "string") {
    return value || "未记录";
  }
  if (value === null || value === undefined) {
    return "未记录";
  }
  return JSON.stringify(value, null, 2);
}

function getRecord(value: unknown, key: string): Record<string, unknown> {
  if (!isObject(value)) {
    return {};
  }
  const nested = value[key];
  return isObject(nested) ? nested : {};
}

function getArray(value: unknown, key: string): unknown[] {
  if (!isObject(value)) {
    return [];
  }
  const nested = value[key];
  return Array.isArray(nested) ? nested : [];
}

function getString(value: unknown, key: string): string {
  if (!isObject(value)) {
    return "";
  }
  const nested = value[key];
  return typeof nested === "string" ? nested : "";
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => String(item)).filter((item) => item.trim());
}

function getNestedRecord(value: unknown, key: string): Record<string, unknown> {
  if (!isObject(value)) {
    return {};
  }
  return getRecord(value, key);
}

function getLogPromptId(log: RequirementAnalysisProviderLog) {
  const audit = log.audit ?? {};
  const promptBundle = getRecord(audit.provider_request, "prompt_bundle");
  const mockContext = getRecord(audit.provider_request, "mock_context");
  const mockStage = getNestedRecord(mockContext, "stage");
  return getString(promptBundle, "prompt_id") || getString(mockStage, "prompt_id");
}

function formatStageLabel(stageId?: string, stageType?: string, promptId?: string) {
  const parts = [stageId || "未记录阶段", promptId || "", stageType || ""].filter(Boolean);
  return parts.join(" / ");
}

function buildWorkingDocumentSegments(text: string, fragments: WorkingDocumentFragment[]) {
  const content = text ?? "";
  const validFragments = [...fragments]
    .filter((fragment) => fragment.end_offset > fragment.start_offset)
    .sort((left, right) => left.start_offset - right.start_offset);
  if (!validFragments.length) {
    return [{ key: "plain-all", text: content, colorToken: "" }];
  }

  const segments: Array<{ key: string; text: string; colorToken: string }> = [];
  let cursor = 0;
  for (const fragment of validFragments) {
    const start = Math.max(cursor, Math.min(content.length, fragment.start_offset));
    const end = Math.max(start, Math.min(content.length, fragment.end_offset));
    if (start > cursor) {
      segments.push({
        key: `plain-${cursor}-${start}`,
        text: content.slice(cursor, start),
        colorToken: "",
      });
    }
    if (end > start) {
      segments.push({
        key: fragment.fragment_id,
        text: content.slice(start, end),
        colorToken: fragment.color_token,
      });
      cursor = end;
    }
  }
  if (cursor < content.length) {
    segments.push({
      key: `plain-${cursor}-${content.length}`,
      text: content.slice(cursor),
      colorToken: "",
    });
  }
  return segments.filter((segment) => segment.text);
}

function SessionSummary({ session }: { session: RequirementAnalysisSession | null }) {
  return (
    <section className="requirement-analysis-lab-panel requirement-analysis-lab-summary">
      <PanelHead title="会话摘要 / 过程产物" subtitle="主视角是会话内临时正文；完成度树和沟通路径作为辅助对照。" />
      {session ? (
        <Tabs
          defaultActiveKey="working-document"
          items={[
            {
              key: "working-document",
              label: "临时正文",
              children: <WorkingDocumentView session={session} />,
            },
            {
              key: "spec-tree",
              label: "需求规格完成度树",
              children: <SpecCompletionTree session={session} />,
            },
            {
              key: "turn-path",
              label: "沟通路径",
              children: <TurnPathView session={session} />,
            },
          ]}
        />
      ) : (
        <div className="requirement-analysis-lab-empty">
          <Text type="secondary">尚未创建会话，暂无摘要。</Text>
        </div>
      )}
    </section>
  );
}

function WorkingDocumentView({ session }: { session: RequirementAnalysisSession }) {
  const viewModel = buildRequirementAnalysisWorkingDocumentViewModel(session);
  const allFragmentIds = useMemo(
    () => viewModel.blocks.flatMap((block) => block.fragments.map((fragment) => fragment.fragment_id)),
    [viewModel.blocks],
  );
  const [selectedRevisionEventTurnId, setSelectedRevisionEventTurnId] = useState<string | null>(null);
  const selectedRevisionEvent = viewModel.revisionEvents.find((event) => event.turnId === selectedRevisionEventTurnId) ?? null;
  const selectedFragmentIds = new Set(selectedRevisionEvent?.fragmentIds ?? []);

  useEffect(() => {
    if (!selectedRevisionEventTurnId) {
      return;
    }
    if (!viewModel.revisionEvents.some((event) => event.turnId === selectedRevisionEventTurnId)) {
      setSelectedRevisionEventTurnId(null);
    }
  }, [allFragmentIds, selectedRevisionEventTurnId, viewModel.revisionEvents]);

  return (
    <div className="requirement-analysis-lab-spec-summary">
      <div className="requirement-analysis-lab-summary-title-row">
        <Text strong>临时正文 / A4 视图</Text>
        <Tag color="blue">focus: {session.active_spec_node_id ?? "已完成"}</Tag>
      </div>
      {viewModel.blocks.length ? (
        <div className="requirement-analysis-lab-working-document">
          <div className="requirement-analysis-lab-working-document-sheet">
            <div className="requirement-analysis-lab-working-document-page" data-testid="requirement-analysis-working-document-page">
              <div className="requirement-analysis-lab-working-document-page-head">
                <Text strong>{viewModel.title}</Text>
                {viewModel.topic ? <Text type="secondary">{viewModel.topic}</Text> : null}
              </div>
              <div className="requirement-analysis-lab-working-document-body">
                {viewModel.blocks.map((block) => (
                  <div className="requirement-analysis-lab-working-document-block" key={block.blockId}>
                    <div className="requirement-analysis-lab-working-document-anchor">
                      <Text type="secondary">{block.displayHeading || block.anchorPath}</Text>
                    </div>
                    <div className="requirement-analysis-lab-working-document-paragraph">
                      {buildWorkingDocumentSegments(block.text, block.fragments).map((segment) => (
                        <span
                          className={
                            segment.colorToken
                              ? `requirement-analysis-lab-revision-highlight ${segment.colorToken} ${
                                  selectedFragmentIds.has(segment.key) ? "is-active" : ""
                                }`
                              : undefined
                          }
                          data-testid={segment.colorToken ? `requirement-analysis-highlight-${segment.key}` : undefined}
                          key={segment.key}
                        >
                          {segment.text}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="requirement-analysis-lab-working-document-revision-rail" aria-label="临时正文修订标注">
              {viewModel.revisionEvents.map((event) => (
                <button
                  aria-label={`定位${formatRequirementAnalysisTurnLabel(event.turnId)}`}
                  className={`requirement-analysis-lab-margin-marker ${event.colorToken} ${
                    selectedRevisionEventTurnId === event.turnId ? "is-active" : ""
                  }`}
                  data-testid={`requirement-analysis-marker-${event.fragmentIds[0]}`}
                  data-marker-group="requirement-analysis-revision-marker"
                  data-turn-id={event.turnId}
                  key={event.turnId}
                  onClick={() => setSelectedRevisionEventTurnId(event.turnId)}
                  type="button"
                >
                  <Text strong>{formatRequirementAnalysisTurnLabel(event.turnId)}</Text>
                  <Text type="secondary">{event.summary || event.reason || "本轮修订"}</Text>
                  {event.fragmentIds.length > 1 ? <Text type="secondary">影响 {event.fragmentIds.length} 处，定位到首次修订位置</Text> : null}
                  {event.deletedTexts.length ? <Text type="secondary">删除：{event.deletedTexts.join("；")}</Text> : null}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="requirement-analysis-lab-empty">
          <Text type="secondary">当前会话尚未形成临时正文。</Text>
        </div>
      )}
    </div>
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
    </div>
  );
}

function TurnPathView({ session }: { session: RequirementAnalysisSession }) {
  return (
    <div className="requirement-analysis-lab-turn-path-panel">
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

function formatDocumentPatchAnchorLabel(
  planRef: string,
  anchorPlanById: Map<string, { display_heading?: string; canonical_clause_heading?: string; template_clause_id: string }>,
) {
  const plan = anchorPlanById.get(planRef);
  if (!plan) {
    return planRef || "未绑定锚点";
  }
  return plan.display_heading || plan.canonical_clause_heading || plan.template_clause_id || planRef;
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
  const previousTargetSpecNodeIds = asStringArray(turn.previous_interaction.target_spec_node_ids);
  const previousOptions = Array.isArray(turn.previous_interaction.options) ? turn.previous_interaction.options : [];
  const confirmedFacts = asStringArray(turn.spec_execution.confirmed_facts);
  const affectedSpecNodes = Array.isArray(turn.spec_execution.affected_spec_nodes) ? turn.spec_execution.affected_spec_nodes : [];
  const documentPatch = Array.isArray(turn.spec_execution.document_patch) ? turn.spec_execution.document_patch : [];
  const anchorPlanById = new Map(
    (Array.isArray(turn.spec_execution.target_anchor_plan) ? turn.spec_execution.target_anchor_plan : []).map((plan) => [
      plan.plan_id,
      plan,
    ]),
  );
  const appliedBlockIds = asStringArray(turn.spec_execution.working_document_update.applied_block_ids);
  const targetReviewPaths = asStringArray(turn.post_update_review.target_review.review_target);
  const missingAspects = asStringArray(turn.post_update_review.target_review.missing_aspects);
  const remainingGaps = asStringArray(turn.post_update_review.global_review.remaining_gaps);
  const nextTargetSpecNodeIds = asStringArray(turn.next_interaction.target_spec_node_ids);
  const nextOptions = Array.isArray(turn.next_interaction.options) ? turn.next_interaction.options : [];
  const decisionTrace = asStringArray(turn.decision_trace);
  return (
    <div className="requirement-analysis-lab-turn-view">
      <div className="requirement-analysis-lab-turn-card is-audit">
        <Text type="secondary">上轮系统留题</Text>
        <div className="requirement-analysis-lab-turn-inline">
          <Tag>{formatInteractionType(turn.previous_interaction.type)}</Tag>
          {previousTargetSpecNodeIds.map((nodeId) => (
            <Tag key={nodeId}>{nodeId}</Tag>
          ))}
        </div>
        <Text strong>{turn.previous_interaction.prompt || "无，用户自由发起。"}</Text>
        {turn.previous_interaction.reason ? <Text type="secondary">{turn.previous_interaction.reason}</Text> : null}
        {previousOptions.length ? <OptionSummary options={previousOptions} /> : null}
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
      {turn.stage_audits?.length ? <StageAuditSummary stageAudits={turn.stage_audits} /> : null}
      <div className="requirement-analysis-lab-turn-card">
        <Text type="secondary">规格补充执行</Text>
        <Text strong>{turn.spec_execution.interpretation.summary}</Text>
        <Text>{turn.spec_execution.assistant_message}</Text>
        <Text strong>确认事实</Text>
        {confirmedFacts.map((fact) => (
          <Text key={fact}>{fact}</Text>
        ))}
        <Text strong>影响节点</Text>
        {affectedSpecNodes.map((node) => (
          <div className="requirement-analysis-lab-affected-node" key={`${node.node_id}-${node.target_section}`}>
            <Text strong>{node.node_id ?? "未绑定节点"}</Text>
            <Text>{node.target_section ?? node.title ?? "未绑定章节"}</Text>
            <Text type="secondary">{node.reason}</Text>
          </div>
        ))}
        <Text strong>正文建议</Text>
        {documentPatch.map((patch) => (
          <div className="requirement-analysis-lab-patch" key={`${patch.plan_ref}-${patch.operation}`}>
            <Text strong>{formatDocumentPatchAnchorLabel(patch.plan_ref, anchorPlanById)}</Text>
            <Text type="secondary">计划引用：{patch.plan_ref}</Text>
            <Text>{patch.content}</Text>
          </div>
        ))}
        <StateChangeSummary stateChanges={turn.spec_execution.state_changes} />
      </div>
      <div className="requirement-analysis-lab-turn-card">
        <Text type="secondary">临时正文应用结果</Text>
        <Text strong>
          应用正文块：
          {appliedBlockIds.length
            ? appliedBlockIds.join("、")
            : "无"}
        </Text>
        <Text>{turn.spec_execution.working_document_update.after_excerpt || "当前未形成临时正文。"}</Text>
      </div>
      <div className="requirement-analysis-lab-turn-card">
        <Text type="secondary">目标范围回看</Text>
        <Tag color={turn.post_update_review.target_review.status === "acceptable" ? "green" : "gold"}>
          {turn.post_update_review.target_review.status}
        </Tag>
        <Text strong>{turn.post_update_review.target_review.reason}</Text>
        {targetReviewPaths.length ? (
          <Text type="secondary">命中范围：{targetReviewPaths.join("、")}</Text>
        ) : null}
        {missingAspects.length ? (
          <>
            <Text strong>章节缺口</Text>
            {missingAspects.map((gap) => (
              <Text key={gap}>{gap}</Text>
            ))}
          </>
        ) : null}
      </div>
      <div className="requirement-analysis-lab-turn-card">
        <Text type="secondary">全局回看</Text>
        <Tag>{turn.post_update_review.global_review.status}</Tag>
        <Text strong>{turn.post_update_review.global_review.summary}</Text>
        {remainingGaps.length ? (
          <>
            <Text strong>剩余缺口</Text>
            {remainingGaps.map((gap) => (
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
          {nextTargetSpecNodeIds.map((nodeId) => (
            <Tag key={nodeId}>{nodeId}</Tag>
          ))}
        </div>
        <Text strong>{turn.next_interaction.prompt || "无，等待用户自由输入。"}</Text>
        {turn.next_interaction.reason ? <Text type="secondary">{turn.next_interaction.reason}</Text> : null}
        {nextOptions.length ? <OptionSummary options={nextOptions} /> : null}
      </div>
      <div className="requirement-analysis-lab-turn-card">
        <Text type="secondary">决策依据</Text>
        <ol>
          {decisionTrace.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function StageAuditSummary({ stageAudits }: { stageAudits: RequirementAnalysisTurnStageAudit[] }) {
  return (
    <div className="requirement-analysis-lab-turn-card is-stage-audit">
      <Text type="secondary">阶段执行审计</Text>
      <div className="requirement-analysis-lab-stage-audit-list">
        {stageAudits.map((stage) => (
          <div className="requirement-analysis-lab-stage-audit-item" key={stage.stage_id}>
            <div className="requirement-analysis-lab-turn-inline">
              <Tag color={stage.stage_kind === "review" ? "purple" : "blue"}>{stage.stage_id}</Tag>
              <Tag>{stage.execution_mode}</Tag>
              <Tag color={stage.validation_status === "accepted" ? "green" : "gold"}>{stage.validation_status}</Tag>
              {stage.blocking_used ? <Tag color="red">阻断</Tag> : null}
            </div>
            <Text strong>{stage.summary}</Text>
            <Text type="secondary">Provider Log：{stage.provider_call_log_id ?? "无独立模型日志"}</Text>
            {stage.adopted_fields.length ? <Text type="secondary">采纳字段：{stage.adopted_fields.join("、")}</Text> : null}
          </div>
        ))}
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

function formatProviderStatus(status: string) {
  if (status === "active") {
    return "已启用";
  }
  if (status === "not_configured") {
    return "未配置";
  }
  return status;
}

function sortRequirementAnalysisProviders(providers: RequirementAnalysisProvider[]) {
  return [...providers].sort((left, right) => providerPriority(left.provider_id) - providerPriority(right.provider_id));
}

function providerPriority(providerId: string) {
  if (providerId === "deepseek") {
    return 0;
  }
  if (providerId === "mock") {
    return 1;
  }
  return 2;
}

function formatQuickOptionInput(option: RequirementAnalysisQuickOption) {
  return `${option.key}，${option.label}`;
}
