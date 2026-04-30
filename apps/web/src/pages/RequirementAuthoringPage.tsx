import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Drawer, Empty, Input, Popover, Segmented, Space, Spin, Tabs, Tag, Typography } from "antd";

import { useArchiveContext } from "../context/ArchiveContext";
import type {
  RequirementAuthoringAnnotation,
  RequirementAuthoringDocumentDetail,
  RequirementAuthoringKnowledgeBinding,
  RequirementAuthoringKnowledgeProvider,
  RequirementAuthoringLayoutRatio,
  RequirementAuthoringTemplate,
  RequirementAuthoringTemplateField,
} from "../lib/api";
import {
  appendRequirementAuthoringMessage,
  bindRequirementAuthoringKnowledge,
  createRequirementAuthoringDocument,
  freezeRequirementAuthoringDocument,
  getRequirementAuthoringDocuments,
  getRequirementAuthoringKnowledgeProviders,
  getRequirementAuthoringTemplates,
  patchRequirementAuthoringFormFields,
  runRequirementAuthoringCheck,
} from "../lib/requirementAuthoring";
import "./RequirementAuthoringPage.css";

const { Text, Title } = Typography;
const { TextArea } = Input;

export function RequirementAuthoringPage() {
  const { activeArchiveId } = useArchiveContext();
  const [templates, setTemplates] = useState<RequirementAuthoringTemplate[]>([]);
  const [knowledgeProviders, setKnowledgeProviders] = useState<RequirementAuthoringKnowledgeProvider[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState<string | null>(null);
  const [selectedDomainId, setSelectedDomainId] = useState<string | null>(null);
  const [knowledgeBinding, setKnowledgeBinding] = useState<RequirementAuthoringKnowledgeBinding | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [currentDocument, setCurrentDocument] = useState<RequirementAuthoringDocumentDetail | null>(null);
  const [ratio, setRatio] = useState<RequirementAuthoringLayoutRatio>("2:3");
  const [questionInput, setQuestionInput] = useState("");
  const [activeAnnotation, setActiveAnnotation] = useState<RequirementAuthoringAnnotation | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        const [templatesResponse, documentsResponse, providersResponse] = await Promise.all([
          getRequirementAuthoringTemplates(),
          getRequirementAuthoringDocuments(),
          getRequirementAuthoringKnowledgeProviders(),
        ]);
        if (cancelled) {
          return;
        }
        const nextTemplates = templatesResponse.data;
        const nextProviders = providersResponse.data.items;
        setTemplates(nextTemplates);
        setKnowledgeProviders(nextProviders);
        setSelectedProviderId(nextProviders[0]?.provider_id ?? null);
        setSelectedDomainId(nextProviders[0]?.domains[0]?.domain_id ?? null);
        setSelectedTemplateId(nextTemplates.find((item) => item.status === "active")?.template_id ?? nextTemplates[0]?.template_id ?? null);
        setCurrentDocument(null);
        setRatio(documentsResponse.data[0]?.layout_ratio ?? "2:3");
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载 P2 规格编写配置失败");
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

  const selectedTemplate = useMemo(
    () => templates.find((item) => item.template_id === selectedTemplateId) ?? templates[0] ?? null,
    [selectedTemplateId, templates],
  );
  const selectedProvider = useMemo(
    () => knowledgeProviders.find((item) => item.provider_id === selectedProviderId) ?? knowledgeProviders[0] ?? null,
    [knowledgeProviders, selectedProviderId],
  );
  const selectedDomain = useMemo(
    () => selectedProvider?.domains.find((item) => item.domain_id === selectedDomainId) ?? selectedProvider?.domains[0] ?? null,
    [selectedDomainId, selectedProvider],
  );

  const quickInputs = selectedTemplate?.questionnaire_policy.quick_inputs ?? ["可以", "更正式", "加超时", "重拟", "继续"];
  const fields = currentDocument?.semantic_state.fields ?? {};

  async function handleCreateDocument() {
    if (!selectedTemplate) {
      return;
    }

    try {
      setSubmitting(true);
      const boundArchiveId = knowledgeBinding?.knowledge_archive.archive_id ?? knowledgeBinding?.domain.domain_id;
      const response = await createRequirementAuthoringDocument({
        title: "未命名软件需求规格说明",
        template_id: selectedTemplate.template_id,
        archive_ids: boundArchiveId ? [boundArchiveId] : activeArchiveId ? [activeArchiveId] : [],
        layout_ratio: ratio,
      });
      setCurrentDocument(response.data);
      setRatio(response.data.layout_ratio);
      setError(null);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "创建规格文档失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleBindKnowledge() {
    if (!selectedProvider || !selectedDomain) {
      return;
    }

    try {
      setSubmitting(true);
      const response = await bindRequirementAuthoringKnowledge(selectedProvider.provider_id, selectedDomain.domain_id);
      setKnowledgeBinding(response.data);
      setError(null);
    } catch (bindError) {
      setError(bindError instanceof Error ? bindError.message : "加载领域知识失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSend(content = questionInput) {
    const normalized = content.trim();
    if (!currentDocument || !normalized) {
      return;
    }

    try {
      setSubmitting(true);
      const response = await appendRequirementAuthoringMessage(currentDocument.document_id, normalized);
      setCurrentDocument(response.data);
      setQuestionInput("");
      setError(null);
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "发送问答输入失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleFieldChange(field: RequirementAuthoringTemplateField, value: string) {
    if (!currentDocument) {
      return;
    }

    const localDocument = {
      ...currentDocument,
      semantic_state: {
        ...currentDocument.semantic_state,
        fields: {
          ...currentDocument.semantic_state.fields,
          [field.field_key]: value,
        },
      },
    };
    setCurrentDocument(localDocument);

    try {
      const response = await patchRequirementAuthoringFormFields(currentDocument.document_id, { [field.field_key]: value });
      setCurrentDocument(response.data);
      setError(null);
    } catch (patchError) {
      setError(patchError instanceof Error ? patchError.message : "同步表单字段失败");
    }
  }

  async function handleRunCheck() {
    if (!currentDocument) {
      return;
    }

    try {
      setSubmitting(true);
      const response = await runRequirementAuthoringCheck(currentDocument.document_id);
      setCurrentDocument(response.data);
      setError(null);
    } catch (checkError) {
      setError(checkError instanceof Error ? checkError.message : "缺口检查失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleFreeze() {
    if (!currentDocument) {
      return;
    }

    try {
      setSubmitting(true);
      const response = await freezeRequirementAuthoringDocument(currentDocument.document_id);
      setCurrentDocument(response.data);
      setError(null);
    } catch (freezeError) {
      setError(freezeError instanceof Error ? freezeError.message : "冻结版本失败");
    } finally {
      setSubmitting(false);
    }
  }

  function openAnnotation(clauseId: string) {
    setActiveAnnotation(currentDocument?.annotations.find((item) => item.clause_id === clauseId) ?? null);
  }

  const settingsContent = (
    <Space direction="vertical" size={10} style={{ minWidth: 260 }}>
      <Text strong>当前规格模板</Text>
      <Segmented
        block
        value={selectedTemplateId ?? undefined}
        options={templates.map((item) => ({ label: item.template_code, value: item.template_id }))}
        onChange={(value) => setSelectedTemplateId(String(value))}
      />
      <Text type="secondary">知识库：{activeArchiveId ?? "默认知识库"}</Text>
      <Text type="secondary">配置版本：{selectedTemplate?.status ?? "未加载"}</Text>
    </Space>
  );

  return (
    <div className="requirement-authoring-page requirement-authoring-workbench-page">
      <div className="requirement-authoring-header">
        <div>
          <Title level={2} className="requirement-authoring-title">
            P2 专家需求规格编写工作台
          </Title>
          <Text type="secondary">面向专家的标准需求规格说明正文编写、校对、检查与冻结。</Text>
        </div>
        <div className="requirement-authoring-actions">
          <Segmented
            value={ratio}
            options={[
              { label: "2:3", value: "2:3" },
              { label: "1:1", value: "1:1" },
            ]}
            onChange={(value) => setRatio(value as RequirementAuthoringLayoutRatio)}
          />
          <Popover content={settingsContent} trigger="click" placement="bottomRight">
            <Button>设置</Button>
          </Popover>
          <Button type="primary" loading={submitting} disabled={!selectedTemplate} onClick={() => void handleCreateDocument()}>
            创建规格文档
          </Button>
          <Button disabled={!currentDocument} loading={submitting} onClick={() => void handleRunCheck()}>
            缺口检查
          </Button>
          <Button disabled={!currentDocument} loading={submitting} onClick={() => void handleFreeze()}>
            冻结版本
          </Button>
        </div>
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 12 }} /> : null}
      {currentDocument?.frozen_package?.p3_consumable ? (
        <Alert type="success" showIcon message="P3 可消费" style={{ marginBottom: 12 }} />
      ) : null}

      {loading ? (
        <Spin />
      ) : (
        <>
          {!currentDocument ? (
            <KnowledgeBindingPanel
              providers={knowledgeProviders}
              selectedProvider={selectedProvider}
              selectedDomain={selectedDomain}
              binding={knowledgeBinding}
              submitting={submitting}
              onProviderChange={(providerId) => {
                const provider = knowledgeProviders.find((item) => item.provider_id === providerId) ?? null;
                setSelectedProviderId(providerId);
                setSelectedDomainId(provider?.domains[0]?.domain_id ?? null);
                setKnowledgeBinding(null);
              }}
              onDomainChange={(domainId) => {
                setSelectedDomainId(domainId);
                setKnowledgeBinding(null);
              }}
              onBind={() => void handleBindKnowledge()}
            />
          ) : null}

          <div
            data-testid="requirement-authoring-workbench"
            className={`requirement-authoring-shell${ratio === "1:1" ? " is-equal" : ""}`}
          >
          <div className="requirement-authoring-panel requirement-authoring-input-panel">
            <div className="requirement-authoring-ratio-hint">
              <Text type="secondary">可切换分屏</Text>
              {knowledgeBinding ? <Tag color="green">{knowledgeBinding.editor_badge}</Tag> : null}
              <Tag>1:1</Tag>
            </div>
            <Tabs
              items={[
                {
                  key: "question",
                  label: "问答模式",
                  children: currentDocument ? (
                    <QuestionMode
                      quickInputs={quickInputs}
                      currentDocument={currentDocument}
                      questionInput={questionInput}
                      submitting={submitting}
                      onQuestionInputChange={setQuestionInput}
                      onSend={(content) => void handleSend(content)}
                    />
                  ) : (
                    <Empty description="创建规格文档后开始问答协作" />
                  ),
                },
                {
                  key: "form",
                  label: "表单模式",
                  children: currentDocument && selectedTemplate ? (
                    <FormMode
                      template={selectedTemplate}
                      fields={fields}
                      onFieldChange={(field, value) => void handleFieldChange(field, value)}
                    />
                  ) : (
                    <Empty description="创建规格文档后开始表单校对" />
                  ),
                },
              ]}
            />
          </div>

          <div className="requirement-authoring-panel requirement-authoring-document-panel">
            <div className="requirement-authoring-document-toolbar">
              <Space wrap>
                <Text strong>标准需求规格说明</Text>
                <Tag color="green">可导出稿</Tag>
                {currentDocument ? <Tag>{currentDocument.status}</Tag> : null}
                {currentDocument?.check_result ? <Tag>阻断项 {currentDocument.check_result.blocking_count}</Tag> : null}
              </Space>
              <Text type="secondary">{selectedTemplate?.name ?? "未选择模板"}</Text>
            </div>
            <div className="requirement-authoring-document-ribbon" aria-label="文档编辑状态">
              <span>页面 A4</span>
              <span>样式 标准正文</span>
              <span>段落 1.5 倍行距</span>
              <span>导出 DOCX / PDF</span>
            </div>
            {currentDocument ? (
              <StandardDocumentView currentDocument={currentDocument} onOpenAnnotation={openAnnotation} />
            ) : (
              <div className="requirement-authoring-document-canvas">
                <div className="requirement-authoring-empty requirement-authoring-document-paper">
                  <Title level={4}>标准需求规格说明</Title>
                  <Text type="secondary">选择模板并创建文档后，右侧会持续生成标准正文。</Text>
                </div>
              </div>
            )}
          </div>
          </div>
        </>
      )}

      <Drawer title="条款批注" open={Boolean(activeAnnotation)} onClose={() => setActiveAnnotation(null)} width={420}>
        {activeAnnotation ? (
          <Space direction="vertical" size={14} style={{ display: "flex" }}>
            <div>
              <Text strong>{activeAnnotation.clause_id}</Text>
              <Title level={4} style={{ marginTop: 4 }}>
                {activeAnnotation.title}
              </Title>
              <Text>{activeAnnotation.interpretation}</Text>
            </div>
            <div>
              <Text strong>P3 输入映射</Text>
              <div>
                {activeAnnotation.p3_mapping.length > 0
                  ? activeAnnotation.p3_mapping.map((item) => <Tag key={item}>{item}</Tag>)
                  : "暂无映射"}
              </div>
            </div>
            <div>
              <Text strong>来源引用</Text>
              <div>
                {activeAnnotation.source_refs.length > 0
                  ? activeAnnotation.source_refs.map((item) => <Tag key={item}>{item}</Tag>)
                  : "未绑定来源"}
              </div>
            </div>
            {activeAnnotation.pending_confirmations.length > 0 ? (
              <Alert type="warning" showIcon message={activeAnnotation.pending_confirmations.join("；")} />
            ) : null}
          </Space>
        ) : null}
      </Drawer>
    </div>
  );
}

function KnowledgeBindingPanel({
  providers,
  selectedProvider,
  selectedDomain,
  binding,
  submitting,
  onProviderChange,
  onDomainChange,
  onBind,
}: {
  providers: RequirementAuthoringKnowledgeProvider[];
  selectedProvider: RequirementAuthoringKnowledgeProvider | null;
  selectedDomain: RequirementAuthoringKnowledgeProvider["domains"][number] | null;
  binding: RequirementAuthoringKnowledgeBinding | null;
  submitting: boolean;
  onProviderChange: (providerId: string) => void;
  onDomainChange: (domainId: string) => void;
  onBind: () => void;
}) {
  return (
    <section className="requirement-authoring-knowledge-binding" aria-label="P1 知识绑定">
      <div className="requirement-authoring-knowledge-source">
        <div>
          <Title level={4}>P1 知识绑定</Title>
          <Text type="secondary">选择已注册的上游知识服务，按领域拉取知识背景。</Text>
        </div>
        {providers.length ? (
          <div className="requirement-authoring-source-list">
            {providers.map((provider) => (
              <button
                type="button"
                key={provider.provider_id}
                className={`requirement-authoring-source-card${provider.provider_id === selectedProvider?.provider_id ? " is-active" : ""}`}
                onClick={() => onProviderChange(provider.provider_id)}
              >
                <Text strong>P1 知识源</Text>
                <Tag color={provider.status === "online" ? "green" : "orange"}>{provider.status === "online" ? "可用" : "未接入"}</Tag>
              </button>
            ))}
          </div>
        ) : (
          <Empty description="未发现 P1 知识源" />
        )}
      </div>
      <div className="requirement-authoring-domain-picker">
        <div className="requirement-authoring-domain-head">
          <div>
            <Title level={4}>选择领域知识</Title>
            <Text type="secondary">这里选择的是知识背景，不是软件名称；目标软件由后续需求规格编辑确定。</Text>
          </div>
          <Button type="primary" loading={submitting} disabled={!selectedProvider || !selectedDomain} onClick={onBind}>
            加载领域知识
          </Button>
        </div>
        <div className="requirement-authoring-domain-list">
          {selectedProvider?.domains.map((domain) => (
            <button
              type="button"
              key={domain.domain_id}
              className={`requirement-authoring-domain-card${domain.domain_id === selectedDomain?.domain_id ? " is-active" : ""}`}
              onClick={() => onDomainChange(domain.domain_id)}
            >
              <span>
                <Text strong>{domain.domain_name}</Text>
                <Text type="secondary">{domain.domain_summary}</Text>
              </span>
              <Tag color={domain.domain_id === selectedDomain?.domain_id ? "green" : "default"}>
                {domain.domain_id === selectedDomain?.domain_id ? "选中" : "选择"}
              </Tag>
            </button>
          ))}
        </div>
        {binding ? <Alert type="success" showIcon message={binding.editor_badge} /> : null}
      </div>
    </section>
  );
}

function QuestionMode({
  quickInputs,
  currentDocument,
  questionInput,
  submitting,
  onQuestionInputChange,
  onSend,
}: {
  quickInputs: string[];
  currentDocument: RequirementAuthoringDocumentDetail;
  questionInput: string;
  submitting: boolean;
  onQuestionInputChange: (value: string) => void;
  onSend: (content?: string) => void;
}) {
  return (
    <div className="requirement-authoring-question-mode">
      <div className="requirement-authoring-messages">
        {currentDocument.conversation.map((message, index) => (
          <div
            key={message.id}
            className={`requirement-authoring-message${message.role === "user" ? " is-user" : ""}`}
          >
            <Text type="secondary">{message.role === "user" ? "专家" : "系统"}</Text>
            <div>
              {index === 0 && currentDocument.conversation.length > 1
                ? message.content.replace("你可以直接回：可以 / 更正式 / 加超时 / 重拟 / 继续。", "可用短指令继续。")
                : message.content}
            </div>
          </div>
        ))}
      </div>
      <div className="requirement-authoring-quick-row">
        {quickInputs.map((item) => (
          <Button key={item} size="small" onClick={() => onSend(item)}>
            {item}
          </Button>
        ))}
      </div>
      <div className="requirement-authoring-send-row">
        <Input
          value={questionInput}
          placeholder="输入 A、可以、更正式、加超时、重拟，或直接补充一句业务事实"
          onChange={(event) => onQuestionInputChange(event.target.value)}
          onPressEnter={() => onSend()}
        />
        <Button aria-label="发送" type="primary" loading={submitting} onClick={() => onSend()}>
          发送
        </Button>
      </div>
    </div>
  );
}

function FormMode({
  template,
  fields,
  onFieldChange,
}: {
  template: RequirementAuthoringTemplate;
  fields: Record<string, string>;
  onFieldChange: (field: RequirementAuthoringTemplateField, value: string) => void;
}) {
  return (
    <div className="requirement-authoring-form-groups">
      {template.form_groups.map((group) => (
        <div key={group.group_id} className="requirement-authoring-form-group">
          <Text strong className="requirement-authoring-form-title">
            {group.title}
          </Text>
          <Space direction="vertical" size={12} style={{ display: "flex" }}>
            {group.fields.map((field) => (
              <label key={field.field_key}>
                <Text>{field.label}</Text>
                <TextArea
                  aria-label={field.label}
                  value={fields[field.field_key] ?? ""}
                  autoSize={{ minRows: 2, maxRows: 5 }}
                  onChange={(event) => onFieldChange(field, event.target.value)}
                />
              </label>
            ))}
          </Space>
        </div>
      ))}
    </div>
  );
}

function StandardDocumentView({
  currentDocument,
  onOpenAnnotation,
}: {
  currentDocument: RequirementAuthoringDocumentDetail;
  onOpenAnnotation: (clauseId: string) => void;
}) {
  return (
    <div className="requirement-authoring-document-canvas" data-testid="requirement-authoring-document-canvas">
      <article className="requirement-authoring-document-paper" data-testid="requirement-authoring-document-paper">
        <div className="requirement-authoring-document-page-header">
          <span>需求规格说明</span>
          <span>{currentDocument.status === "frozen" ? "冻结版" : "草稿版"}</span>
        </div>
        <Title level={3} className="requirement-authoring-document-title">
          {currentDocument.title}
        </Title>
      {currentDocument.document.sections.map((section) => (
        <section key={section.section_id} className="requirement-authoring-section">
          <Title level={4}>{section.title}</Title>
          {section.clauses.map((clause) => (
            <div key={clause.clause_id} className="requirement-authoring-clause">
              <button
                type="button"
                className="requirement-authoring-clause-id"
                onClick={() => onOpenAnnotation(clause.clause_id)}
              >
                {clause.clause_id}
              </button>
              <div className="requirement-authoring-clause-body">
                <Text strong>{clause.title}</Text>
                <Typography.Paragraph
                  className={`requirement-authoring-clause-content${
                    clause.content.startsWith("待补齐") ? " requirement-authoring-placeholder" : ""
                  }`}
                >
                  {clause.content}
                </Typography.Paragraph>
              </div>
            </div>
          ))}
        </section>
      ))}
      </article>
    </div>
  );
}
