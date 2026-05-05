import { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Button, Drawer, Empty, Input, Modal, Popover, Segmented, Space, Spin, Tabs, Tag, Typography } from "antd";

import { useArchiveContext } from "../context/ArchiveContext";
import type {
  RequirementAuthoringAnnotation,
  RequirementAuthoringDocumentDetail,
  RequirementAuthoringDocumentSummary,
  RequirementAuthoringKnowledgeBinding,
  RequirementAuthoringKnowledgeProvider,
  RequirementAuthoringWorkbenchConfig,
  RequirementAuthoringLayoutRatio,
  RequirementAuthoringTemplate,
  RequirementAuthoringTemplateField,
} from "../lib/api";
import {
  appendRequirementAuthoringMessage,
  bindRequirementAuthoringKnowledge,
  createRequirementAuthoringDocument,
  deleteRequirementAuthoringDocument,
  freezeRequirementAuthoringDocument,
  getRequirementAuthoringDocument,
  patchRequirementAuthoringFormFields,
  runRequirementAuthoringCheck,
  saveRequirementAuthoringDocument,
} from "../lib/requirementAuthoring";
import {
  formatRequirementAuthoringDocumentStatusWithConfig,
  getRequirementAuthoringWorkbenchAction,
  getRequirementAuthoringWorkbenchActionLabel,
  isRequirementAuthoringDocumentEditable,
} from "../lib/requirementAuthoringWorkbenchViewModel";
import { useRequirementAuthoringWorkbenchBootstrap } from "../lib/useRequirementAuthoringWorkbenchBootstrap";
import "./RequirementAuthoringPage.css";

const { Text, Title } = Typography;
const { TextArea } = Input;

function formatKnowledgeDomainLabel(domainName: string): string {
  return domainName.replace(/领域知识$/, "").trim() || domainName;
}

function toDocumentSummary(document: RequirementAuthoringDocumentDetail): RequirementAuthoringDocumentSummary {
  return {
    document_id: document.document_id,
    title: document.title,
    template_id: document.template_id,
    status: document.status,
    layout_ratio: document.layout_ratio,
    archive_ids: document.archive_ids,
    updated_at: document.updated_at,
  };
}

export function RequirementAuthoringPage() {
  const { activeArchiveId } = useArchiveContext();
  const {
    workbenchConfig,
    templates: bootstrappedTemplates,
    documents: bootstrappedDocuments,
    knowledgeProviders: bootstrappedKnowledgeProviders,
    loading,
    error: bootstrapError,
  } = useRequirementAuthoringWorkbenchBootstrap();
  const [templates, setTemplates] = useState<RequirementAuthoringTemplate[]>([]);
  const [documents, setDocuments] = useState<RequirementAuthoringDocumentSummary[]>([]);
  const [knowledgeProviders, setKnowledgeProviders] = useState<typeof bootstrappedKnowledgeProviders>([]);
  const [selectedProviderId, setSelectedProviderId] = useState<string | null>(null);
  const [selectedDomainId, setSelectedDomainId] = useState<string | null>(null);
  const [knowledgeBinding, setKnowledgeBinding] = useState<RequirementAuthoringKnowledgeBinding | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [currentDocument, setCurrentDocument] = useState<RequirementAuthoringDocumentDetail | null>(null);
  const [documentTitleDraft, setDocumentTitleDraft] = useState("");
  const [documentTitleDirty, setDocumentTitleDirty] = useState(false);
  const titleDirtyRef = useRef(false);
  const titleSavePromiseRef = useRef<Promise<RequirementAuthoringDocumentDetail | null> | null>(null);
  const contextDirtyRef = useRef(false);
  const [contextDirty, setContextDirty] = useState(false);
  const [ratio, setRatio] = useState<RequirementAuthoringLayoutRatio>("2:3");
  const [questionInput, setQuestionInput] = useState("");
  const [activeAnnotation, setActiveAnnotation] = useState<RequirementAuthoringAnnotation | null>(null);
  const [knowledgeModalOpen, setKnowledgeModalOpen] = useState(false);
  const [openModalOpen, setOpenModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workbenchConfig) {
      return;
    }
    setTemplates(bootstrappedTemplates);
    setDocuments(bootstrappedDocuments);
    setKnowledgeProviders(bootstrappedKnowledgeProviders);
    setSelectedProviderId((current) => current ?? bootstrappedKnowledgeProviders[0]?.provider_id ?? null);
    setSelectedDomainId((current) => current ?? bootstrappedKnowledgeProviders[0]?.domains[0]?.domain_id ?? null);
    setSelectedTemplateId((current) =>
      current ?? bootstrappedTemplates.find((item) => item.status === "active")?.template_id ?? bootstrappedTemplates[0]?.template_id ?? null,
    );
    setDocumentTitleDraft((current) => current || workbenchConfig.defaults.document_title);
    setRatio((current) => bootstrappedDocuments[0]?.layout_ratio ?? current ?? workbenchConfig.defaults.layout_ratio);
    setError(null);
  }, [bootstrappedDocuments, bootstrappedKnowledgeProviders, bootstrappedTemplates, workbenchConfig]);

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
  const templateButtonLabel = selectedTemplate ? `文档模板：${selectedTemplate.template_code}号` : "文档模板：未选择";
  const knowledgeButtonLabel = knowledgeBinding
    ? `领域知识：${formatKnowledgeDomainLabel(knowledgeBinding.domain.domain_name)}`
    : "领域知识：未选择";
  const createDocumentAction = getRequirementAuthoringWorkbenchAction(workbenchConfig, "create_document");
  const deleteDocumentAction = getRequirementAuthoringWorkbenchAction(workbenchConfig, "delete_document");
  const currentDocumentEditable = currentDocument ? isRequirementAuthoringDocumentEditable(currentDocument.status, workbenchConfig) : false;
  const effectiveError = error ?? bootstrapError;

  const boundArchiveId = knowledgeBinding?.knowledge_archive.archive_id ?? knowledgeBinding?.domain.domain_id;

  function markContextDirty() {
    contextDirtyRef.current = true;
    setContextDirty(true);
  }

  function applyServerDocument(document: RequirementAuthoringDocumentDetail, options: { preserveDirtyTitle?: boolean } = {}) {
    const shouldPreserveTitle =
      options.preserveDirtyTitle === true &&
      titleDirtyRef.current &&
      currentDocument?.document_id === document.document_id;
    const visibleDocument = shouldPreserveTitle ? { ...document, title: documentTitleDraft } : document;
    setCurrentDocument(visibleDocument);
    if (!shouldPreserveTitle) {
      setDocumentTitleDraft(document.title);
      titleDirtyRef.current = false;
      setDocumentTitleDirty(false);
    }
    if (!contextDirtyRef.current) {
      setSelectedTemplateId(document.template_id);
      setKnowledgeBinding(document.semantic_state.knowledge_binding ?? null);
      if (document.semantic_state.knowledge_binding?.provider.provider_id) {
        setSelectedProviderId(document.semantic_state.knowledge_binding.provider.provider_id);
      }
      if (document.semantic_state.knowledge_binding?.domain.domain_id) {
        setSelectedDomainId(document.semantic_state.knowledge_binding.domain.domain_id);
      }
    }
    setDocuments((current) => [
      toDocumentSummary(visibleDocument),
      ...current.filter((item) => item.document_id !== document.document_id),
    ]);
    return visibleDocument;
  }

  async function saveEditorMetadataIfDirty() {
    if (titleSavePromiseRef.current) {
      return titleSavePromiseRef.current;
    }
    if (!currentDocument || (!titleDirtyRef.current && !contextDirtyRef.current) || !currentDocumentEditable) {
      return currentDocument;
    }
    const documentId = currentDocument.document_id;
    const title = documentTitleDraft;
    const nextArchiveIds = knowledgeBinding ? (boundArchiveId ? [boundArchiveId] : currentDocument.archive_ids) : [];
    titleSavePromiseRef.current = saveRequirementAuthoringDocument(documentId, {
      title,
      template_id: selectedTemplateId,
      archive_ids: nextArchiveIds,
      knowledge_binding: knowledgeBinding,
    })
      .then((response) => {
        titleDirtyRef.current = false;
        setDocumentTitleDirty(false);
        contextDirtyRef.current = false;
        setContextDirty(false);
        return applyServerDocument(response.data, { preserveDirtyTitle: false });
      })
      .finally(() => {
        titleSavePromiseRef.current = null;
      });
    return titleSavePromiseRef.current;
  }

  async function handleCreateDocument() {
    if (!selectedTemplate || !workbenchConfig) {
      return;
    }

    try {
      setSubmitting(true);
      const response = await createRequirementAuthoringDocument({
        title: workbenchConfig.defaults.document_title,
        template_id: selectedTemplate.template_id,
        archive_ids: boundArchiveId ? [boundArchiveId] : activeArchiveId ? [activeArchiveId] : [],
        layout_ratio: ratio,
      });
      applyServerDocument(response.data);
      setRatio(response.data.layout_ratio);
      setNotice(null);
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
      markContextDirty();
      setKnowledgeModalOpen(false);
      setNotice(null);
      setError(null);
    } catch (bindError) {
      setError(bindError instanceof Error ? bindError.message : "加载领域知识失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteDocument() {
    if (!currentDocument) {
      return;
    }

    try {
      setSubmitting(true);
      await deleteRequirementAuthoringDocument(currentDocument.document_id);
      setDocuments((current) => current.filter((item) => item.document_id !== currentDocument.document_id));
      setCurrentDocument(null);
      setDocumentTitleDraft(workbenchConfig?.defaults.document_title ?? "");
      titleDirtyRef.current = false;
      setDocumentTitleDirty(false);
      contextDirtyRef.current = false;
      setContextDirty(false);
      setActiveAnnotation(null);
      setDeleteModalOpen(false);
      setNotice("文档已删除");
      setError(null);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "删除文档失败");
    } finally {
      setSubmitting(false);
    }
  }

  function handleSaveDraft() {
    if (!currentDocument) {
      return;
    }
    void saveCurrentDocument();
  }

  async function saveCurrentDocument(options: { silent?: boolean } = {}) {
    if (!currentDocument) {
      return;
    }
    try {
      setSubmitting(true);
      const response = await saveRequirementAuthoringDocument(currentDocument.document_id, {
        title: documentTitleDraft,
        template_id: selectedTemplateId,
        archive_ids: knowledgeBinding ? (boundArchiveId ? [boundArchiveId] : currentDocument.archive_ids) : [],
        knowledge_binding: knowledgeBinding,
      });
      contextDirtyRef.current = false;
      setContextDirty(false);
      applyServerDocument(response.data);
      if (!options.silent) {
        setNotice("草稿已保存");
      }
      setError(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "保存草稿失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleOpenDocument(documentId: string) {
    try {
      setSubmitting(true);
      const response = await getRequirementAuthoringDocument(documentId);
      contextDirtyRef.current = false;
      setContextDirty(false);
      applyServerDocument(response.data);
      setRatio(response.data.layout_ratio);
      setSelectedTemplateId(response.data.template_id);
      setOpenModalOpen(false);
      setNotice(null);
      setError(null);
    } catch (openError) {
      setError(openError instanceof Error ? openError.message : "打开文档失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSend(content = questionInput) {
    const normalized = content.trim();
    if (!currentDocument || !currentDocumentEditable || !normalized) {
      return;
    }

    try {
      setSubmitting(true);
      const activeDocument = await saveEditorMetadataIfDirty();
      if (!activeDocument) {
        return;
      }
      const response = await appendRequirementAuthoringMessage(activeDocument.document_id, normalized);
      applyServerDocument(response.data, { preserveDirtyTitle: true });
      setQuestionInput("");
      setError(null);
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "发送问答输入失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleFieldChange(field: RequirementAuthoringTemplateField, value: string) {
    if (!currentDocument || !currentDocumentEditable) {
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
      await saveEditorMetadataIfDirty();
      const response = await patchRequirementAuthoringFormFields(currentDocument.document_id, { [field.field_key]: value });
      applyServerDocument(response.data, { preserveDirtyTitle: true });
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
      const activeDocument = await saveEditorMetadataIfDirty();
      if (!activeDocument) {
        return;
      }
      const response = await runRequirementAuthoringCheck(activeDocument.document_id);
      applyServerDocument(response.data, { preserveDirtyTitle: true });
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
      const activeDocument = await saveEditorMetadataIfDirty();
      if (!activeDocument) {
        return;
      }
      const response = await freezeRequirementAuthoringDocument(activeDocument.document_id);
      applyServerDocument(response.data, { preserveDirtyTitle: true });
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
        options={templates.map((item) => ({ label: `${item.template_code}号`, value: item.template_id }))}
        onChange={(value) => {
          setSelectedTemplateId(String(value));
          markContextDirty();
        }}
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
            {workbenchConfig?.page.title ?? "加载工作台配置中"}
          </Title>
          <Text type="secondary">{workbenchConfig?.page.subtitle ?? "加载工作台配置中..."}</Text>
        </div>
        <div className="requirement-authoring-actions">
          <Segmented
            value={ratio}
            options={(workbenchConfig?.layout_options ?? []).map((item) => ({ label: item.label, value: item.ratio }))}
            onChange={(value) => setRatio(value as RequirementAuthoringLayoutRatio)}
          />
          <Popover content={settingsContent} trigger="click" placement="bottomRight">
            <Button>{templateButtonLabel}</Button>
          </Popover>
          <Button onClick={() => setKnowledgeModalOpen(true)}>
            {knowledgeButtonLabel}
          </Button>
          <Button
            type={createDocumentAction?.style === "primary" ? "primary" : "default"}
            loading={submitting}
            disabled={!selectedTemplate || !workbenchConfig}
            onClick={() => void handleCreateDocument()}
          >
            {getRequirementAuthoringWorkbenchActionLabel(workbenchConfig, "create_document", "新建文档")}
          </Button>
          <Button onClick={() => setOpenModalOpen(true)}>
            {getRequirementAuthoringWorkbenchActionLabel(workbenchConfig, "open_document", "打开文档")}
          </Button>
          <Button disabled={!currentDocument || !currentDocumentEditable} loading={submitting} onClick={handleSaveDraft}>
            {getRequirementAuthoringWorkbenchActionLabel(workbenchConfig, "save_draft", "保存草稿")}
          </Button>
          <Button danger={deleteDocumentAction?.danger ?? true} disabled={!currentDocument} onClick={() => setDeleteModalOpen(true)}>
            {getRequirementAuthoringWorkbenchActionLabel(workbenchConfig, "delete_document", "删除文档")}
          </Button>
          <Button disabled={!currentDocument} loading={submitting} onClick={() => void handleRunCheck()}>
            {getRequirementAuthoringWorkbenchActionLabel(workbenchConfig, "run_check", "缺口检查")}
          </Button>
          <Button disabled={!currentDocument} loading={submitting} onClick={() => void handleFreeze()}>
            {getRequirementAuthoringWorkbenchActionLabel(workbenchConfig, "freeze", "冻结版本")}
          </Button>
        </div>
      </div>

      {effectiveError ? <Alert type="error" showIcon message={effectiveError} style={{ marginBottom: 12 }} /> : null}
      {notice ? <Alert type="success" showIcon message={notice} style={{ marginBottom: 12 }} /> : null}
      {currentDocument?.frozen_package?.p3_consumable ? (
        <Alert type="success" showIcon message="P3 可消费" style={{ marginBottom: 12 }} />
      ) : null}
      <div className="requirement-authoring-document-namebar">
        <Text strong>文档名称</Text>
        <Input
          aria-label="文档名称"
          value={documentTitleDraft}
          disabled={!currentDocument || !currentDocumentEditable}
          placeholder={workbenchConfig?.defaults.document_title ?? "等待配置加载"}
          onChange={(event) => {
            const nextTitle = event.target.value;
            setDocumentTitleDraft(nextTitle);
            titleDirtyRef.current = true;
            setDocumentTitleDirty(true);
            setCurrentDocument((document) => (document ? { ...document, title: nextTitle } : document));
          }}
          onBlur={() => {
            if (documentTitleDirty) {
              void saveCurrentDocument({ silent: true });
            }
          }}
        />
        {currentDocument ? (
          <Text type="secondary">
            {documentTitleDirty || contextDirty ? "名称或上下文未保存，失焦或继续编辑时自动保存。" : "名称、模板和领域知识已同步到文档。"}
          </Text>
        ) : (
          <Text type="secondary">新建或打开文档后可编辑。</Text>
        )}
      </div>

      {loading ? (
        <Spin />
      ) : (
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
                      disabled={!currentDocumentEditable}
                      onQuestionInputChange={setQuestionInput}
                      onSend={(content) => void handleSend(content)}
                    />
                  ) : (
                      <Empty description={workbenchConfig?.empty_states.question_mode ?? "等待工作台配置加载"} />
                  ),
                },
                {
                  key: "form",
                  label: "表单模式",
                  children: currentDocument && selectedTemplate ? (
                    <FormMode
                      template={selectedTemplate}
                      fields={fields}
                      disabled={!currentDocumentEditable}
                      onFieldChange={(field, value) => void handleFieldChange(field, value)}
                    />
                  ) : (
                    <Empty description={workbenchConfig?.empty_states.form_mode ?? "等待工作台配置加载"} />
                  ),
                },
              ]}
            />
          </div>

          <div className="requirement-authoring-panel requirement-authoring-document-panel">
            <div className="requirement-authoring-document-toolbar">
              <Space wrap>
                <Text strong>{workbenchConfig?.document_surface.title ?? "文档区配置加载中"}</Text>
                {(workbenchConfig?.document_surface.badges ?? []).map((badge) => (
                  <Tag color="green" key={badge}>
                    {badge}
                  </Tag>
                ))}
                {currentDocument ? <Tag>{formatRequirementAuthoringDocumentStatusWithConfig(currentDocument.status, workbenchConfig)}</Tag> : null}
                {currentDocument?.check_result ? <Tag>阻断项 {currentDocument.check_result.blocking_count}</Tag> : null}
              </Space>
              <Text type="secondary">{selectedTemplate?.name ?? "未选择模板"}</Text>
            </div>
            <div className="requirement-authoring-document-ribbon" aria-label="文档编辑状态">
              {(workbenchConfig?.document_surface.ribbon ?? []).map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
            {currentDocument ? (
              <StandardDocumentView currentDocument={currentDocument} onOpenAnnotation={openAnnotation} />
            ) : (
              <div className="requirement-authoring-document-canvas">
                <div className="requirement-authoring-empty requirement-authoring-document-paper">
                  <Title level={4}>{workbenchConfig?.document_surface.title ?? "文档区配置加载中"}</Title>
                  <Text type="secondary">{workbenchConfig?.empty_states.document ?? "等待工作台配置加载"}</Text>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <Modal
        title="设置领域知识"
        open={knowledgeModalOpen}
        onCancel={() => setKnowledgeModalOpen(false)}
        footer={[
          <Button
            key="clear"
            aria-label="清除绑定"
            onClick={() => {
              setKnowledgeBinding(null);
              markContextDirty();
            }}
          >
            清除绑定
          </Button>,
          <Button key="close" aria-label="关闭" onClick={() => setKnowledgeModalOpen(false)}>
            关闭
          </Button>,
          <Button key="apply" type="primary" loading={submitting} disabled={!selectedProvider || !selectedDomain} onClick={() => void handleBindKnowledge()}>
            应用领域知识
          </Button>,
        ]}
        width={760}
      >
        <KnowledgeBindingPanel
          providers={knowledgeProviders}
          selectedProvider={selectedProvider}
          selectedDomain={selectedDomain}
          binding={knowledgeBinding}
          onProviderChange={(providerId) => {
            const provider = knowledgeProviders.find((item) => item.provider_id === providerId) ?? null;
            setSelectedProviderId(providerId);
            setSelectedDomainId(provider?.domains[0]?.domain_id ?? null);
            setKnowledgeBinding(null);
            markContextDirty();
          }}
          onDomainChange={(domainId) => {
            setSelectedDomainId(domainId);
            setKnowledgeBinding(null);
            markContextDirty();
          }}
        />
      </Modal>

      <Modal
        title="打开文档 / 草稿"
        open={openModalOpen}
        onCancel={() => setOpenModalOpen(false)}
        footer={[
          <Button key="close" aria-label="关闭" onClick={() => setOpenModalOpen(false)}>
            关闭
          </Button>,
        ]}
        width={760}
      >
        <Text type="secondary" className="requirement-authoring-open-note">
          打开后会恢复右侧标准正文、左侧问答记录、表单字段、批注和检查状态。
        </Text>
        <DocumentOpenList
          documents={documents}
          templates={templates}
          currentDocumentId={currentDocument?.document_id ?? null}
          submitting={submitting}
          workbenchConfig={workbenchConfig}
          onOpen={(documentId) => void handleOpenDocument(documentId)}
        />
      </Modal>

      <Modal
        title="删除当前规格文档？"
        open={deleteModalOpen}
        onCancel={() => setDeleteModalOpen(false)}
        footer={[
          <Button key="cancel" aria-label="取消" onClick={() => setDeleteModalOpen(false)}>
            取消
          </Button>,
          <Button key="delete" danger type="primary" loading={submitting} onClick={() => void handleDeleteDocument()}>
            确认删除
          </Button>,
        ]}
      >
        <Text type="secondary">删除后当前编辑态会清空，需要重新新建文档。</Text>
      </Modal>

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
  onProviderChange,
  onDomainChange,
}: {
  providers: RequirementAuthoringKnowledgeProvider[];
  selectedProvider: RequirementAuthoringKnowledgeProvider | null;
  selectedDomain: RequirementAuthoringKnowledgeProvider["domains"][number] | null;
  binding: RequirementAuthoringKnowledgeBinding | null;
  onProviderChange: (providerId: string) => void;
  onDomainChange: (domainId: string) => void;
}) {
  return (
    <section className="requirement-authoring-knowledge-dialog" aria-label="领域知识设置">
      <div className="requirement-authoring-knowledge-source">
        <div>
          <Title level={4}>知识来源</Title>
          <Text type="secondary">选择可用的领域知识来源。这里不决定软件名称，也不生成正文。</Text>
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
        <div>
          <Title level={4}>选择领域知识</Title>
          <Text type="secondary">可在创建文档前后随时替换或清除。</Text>
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

function DocumentOpenList({
  documents,
  templates,
  currentDocumentId,
  submitting,
  workbenchConfig,
  onOpen,
}: {
  documents: RequirementAuthoringDocumentSummary[];
  templates: RequirementAuthoringTemplate[];
  currentDocumentId: string | null;
  submitting: boolean;
  workbenchConfig: RequirementAuthoringWorkbenchConfig | null;
  onOpen: (documentId: string) => void;
}) {
  const templateCodeById = new Map(templates.map((template) => [template.template_id, template.template_code]));

  if (!documents.length) {
    return <Empty description="暂无可打开的规格文档" />;
  }

  return (
    <div className="requirement-authoring-open-list">
      {documents.map((document) => (
        <div key={document.document_id} className={`requirement-authoring-open-item${document.document_id === currentDocumentId ? " is-current" : ""}`}>
          <div>
            <Text strong>{document.title}</Text>
            <div className="requirement-authoring-open-meta">
              <Tag>{templateCodeById.get(document.template_id) ?? "未知"}号</Tag>
              <Tag>{formatRequirementAuthoringDocumentStatusWithConfig(document.status, workbenchConfig)}</Tag>
              <Text type="secondary">{new Date(document.updated_at).toLocaleString()}</Text>
            </div>
          </div>
          <Button
            aria-label="打开"
            loading={submitting}
            disabled={document.document_id === currentDocumentId}
            onClick={() => onOpen(document.document_id)}
          >
            打开
          </Button>
        </div>
      ))}
    </div>
  );
}

function QuestionMode({
  quickInputs,
  currentDocument,
  questionInput,
  submitting,
  disabled,
  onQuestionInputChange,
  onSend,
}: {
  quickInputs: string[];
  currentDocument: RequirementAuthoringDocumentDetail;
  questionInput: string;
  submitting: boolean;
  disabled: boolean;
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
          <Button key={item} size="small" disabled={disabled} onClick={() => onSend(item)}>
            {item}
          </Button>
        ))}
      </div>
      <div className="requirement-authoring-send-row">
        <Input
          value={questionInput}
          disabled={disabled}
          placeholder="输入 A、可以、更正式、加超时、重拟，或直接补充一句业务事实"
          onChange={(event) => onQuestionInputChange(event.target.value)}
          onPressEnter={() => onSend()}
        />
        <Button aria-label="发送" type="primary" loading={submitting} disabled={disabled} onClick={() => onSend()}>
          发送
        </Button>
      </div>
    </div>
  );
}

function FormMode({
  template,
  fields,
  disabled,
  onFieldChange,
}: {
  template: RequirementAuthoringTemplate;
  fields: Record<string, string>;
  disabled: boolean;
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
                  disabled={disabled}
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
          {currentDocument.document.title}
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
