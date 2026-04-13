import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Divider,
  Empty,
  Grid,
  Input,
  List,
  Select,
  Space,
  Spin,
  Steps,
  Tag,
  Typography,
  message,
} from "antd";

import { ValidationDrawer } from "./ValidationDrawer";
import { useArchiveContext } from "../context/ArchiveContext";
import {
  completeRequirementDraft,
  createRequirementDraft,
  exportRequirementDraft,
  updateRequirementDraft,
} from "../lib/applicationModeling";
import type {
  ApplicationRequirementDraft,
  ApplicationRequirementDraftEnvelope,
  ApplicationRequirementDraftExport,
  ApplicationRequirementKnowledgeReference,
  ApplicationRequirementManualAddition,
  RequirementRecommendation,
  RequirementStep,
} from "../lib/api";

const stepDefinitions: Array<{
  key: RequirementStep;
  title: string;
  question: string;
  hint: string;
}> = [
  {
    key: "goal",
    title: "业务目标",
    question: "你想解决什么业务问题？",
    hint: "先明确业务痛点、期望结果和衡量标准，后面的使用对象、流程和承载方式才会收敛。",
  },
  {
    key: "audience",
    title: "使用对象",
    question: "谁会使用这个应用？",
    hint: "按真实业务对象划分，不用技术术语，直接写岗位、职责和使用方式。",
  },
  {
    key: "flow",
    title: "核心流程",
    question: "这个应用要承载哪些关键流程？",
    hint: "优先圈定核心办理链路，再考虑协同、补充和辅助流程。",
  },
  {
    key: "object_event",
    title: "关键信息与动作",
    question: "这个应用要围绕哪些信息对象和关键动作展开？",
    hint: "信息对象决定表单与列表，关键动作决定按钮、待办和状态变化。",
  },
  {
    key: "structure",
    title: "应用承载方式",
    question: "最终应用需要用哪些页面和工作空间来承载？",
    hint: "这里先确定承载形态，不做组件复用决策，也不进入开发实现。",
  },
];

const sourceLabels = {
  recommended_common: "通用建议",
  recommended_domain: "领域知识",
  manual: "手工补充",
} as const;

const pageTypeOptions = [
  { value: "task_form", label: "办理页" },
  { value: "overview", label: "总览页" },
  { value: "tracking", label: "进度页" },
  { value: "dashboard", label: "监控页" },
];

type DraftState = {
  draft: ApplicationRequirementDraft | null;
  recommendations: ApplicationRequirementDraftEnvelope["recommendations"];
};

type QuickInputs = {
  audienceName: string;
  audienceDescription: string;
  roleName: string;
  roleSummary: string;
  flowName: string;
  flowPriority: string;
  objectName: string;
  objectDescription: string;
  eventName: string;
  eventDescription: string;
  workspaceName: string;
  pageName: string;
  pageType: string;
};

const emptyRecommendations = {
  goal: [],
  audience: [],
  flow: [],
  object_event: [],
  structure: [],
} as ApplicationRequirementDraftEnvelope["recommendations"];

const initialQuickInputs: QuickInputs = {
  audienceName: "",
  audienceDescription: "",
  roleName: "",
  roleSummary: "",
  flowName: "",
  flowPriority: "high",
  objectName: "",
  objectDescription: "",
  eventName: "",
  eventDescription: "",
  workspaceName: "",
  pageName: "",
  pageType: "task_form",
};

function createLocalId(prefix: string) {
  return `${prefix}-${Math.random().toString(36).slice(2, 8)}`;
}

export function ApplicationRequirementModeler() {
  const screens = Grid.useBreakpoint();
  const { activeArchiveId } = useArchiveContext();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [draftState, setDraftState] = useState<DraftState>({ draft: null, recommendations: emptyRecommendations });
  const [quickInputs, setQuickInputs] = useState<QuickInputs>(initialQuickInputs);
  const [exportOpen, setExportOpen] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportData, setExportData] = useState<ApplicationRequirementDraftExport | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDraft() {
      if (!activeArchiveId) {
        setDraftState({ draft: null, recommendations: emptyRecommendations });
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const response = await createRequirementDraft({ archive_id: activeArchiveId });
        if (cancelled) {
          return;
        }
        setDraftState(response.data);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "初始化建模草稿失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadDraft();
    return () => {
      cancelled = true;
    };
  }, [activeArchiveId]);

  const draft = draftState.draft;
  const currentStepDefinition = useMemo(
    () => stepDefinitions.find((item) => item.key === draft?.current_step) ?? stepDefinitions[0],
    [draft?.current_step],
  );
  const rightColumnMinWidth = screens.xl ? 360 : 320;

  function updateDraftLocally(mutator: (current: ApplicationRequirementDraft) => ApplicationRequirementDraft) {
    setDraftState((current) => {
      if (!current.draft) {
        return current;
      }
      return { ...current, draft: mutator(current.draft) };
    });
  }

  function updateQuickInput<K extends keyof QuickInputs>(key: K, value: QuickInputs[K]) {
    setQuickInputs((current) => ({ ...current, [key]: value }));
  }

  function changeStep(step: RequirementStep) {
    updateDraftLocally((current) => ({ ...current, current_step: step }));
  }

  function addKnowledgeReference(
    currentReferences: ApplicationRequirementKnowledgeReference[],
    recommendation: RequirementRecommendation,
    sourceType: string,
  ) {
    if (!recommendation.related_knowledge_id) {
      return currentReferences;
    }
    if (currentReferences.some((item) => item.source_id === recommendation.related_knowledge_id)) {
      return currentReferences;
    }
    return [
      ...currentReferences,
      {
        source_type: sourceType,
        source_id: recommendation.related_knowledge_id,
        source_name: recommendation.name,
      },
    ];
  }

  function addManualAddition(
    currentAdditions: ApplicationRequirementManualAddition[],
    targetType: string,
    name: string,
  ) {
    if (currentAdditions.some((item) => item.target_type === targetType && item.name === name)) {
      return currentAdditions;
    }
    return [...currentAdditions, { target_type: targetType, name }];
  }

  function applyGoalRecommendation(item: RequirementRecommendation) {
    updateDraftLocally((current) => ({
      ...current,
      application_goal: {
        ...current.application_goal,
        target_outcome: current.application_goal.target_outcome || item.name,
      },
    }));
  }

  function applyAudienceRecommendation(item: RequirementRecommendation) {
    updateDraftLocally((current) => {
      if (current.audiences.some((audience) => audience.name === item.name)) {
        return current;
      }
      return {
        ...current,
        audiences: [
          ...current.audiences,
          {
            id: createLocalId("audience"),
            name: item.name,
            description: item.description,
          },
        ],
      };
    });
  }

  function applyFlowRecommendation(item: RequirementRecommendation) {
    updateDraftLocally((current) => {
      if (current.business_flows.some((flow) => flow.name === item.name)) {
        return current;
      }
      return {
        ...current,
        business_flows: [
          ...current.business_flows,
          {
            id: createLocalId("flow"),
            name: item.name,
            scope: "core",
            priority: "high",
            participants: current.roles.map((role) => role.id),
          },
        ],
        knowledge_references:
          item.source === "recommended_domain"
            ? addKnowledgeReference(current.knowledge_references, item, "domain")
            : current.knowledge_references,
      };
    });
  }

  function applyObjectEventRecommendation(item: RequirementRecommendation) {
    updateDraftLocally((current) => {
      const isEvent = item.tags.includes("领域事件");
      return {
        ...current,
        business_objects: isEvent
          ? current.business_objects
          : current.business_objects.some((entry) => entry.name === item.name)
            ? current.business_objects
            : [
                ...current.business_objects,
                {
                  id: createLocalId("object"),
                  name: item.name,
                  description: item.description,
                },
              ],
        key_events: isEvent
          ? current.key_events.some((entry) => entry.name === item.name)
            ? current.key_events
            : [
                ...current.key_events,
                {
                  id: createLocalId("event"),
                  name: item.name,
                  description: item.description,
                },
              ]
          : current.key_events,
        knowledge_references:
          item.source === "recommended_domain"
            ? addKnowledgeReference(current.knowledge_references, item, isEvent ? "event" : "entity")
            : current.knowledge_references,
      };
    });
  }

  function applyStructureRecommendation(item: RequirementRecommendation) {
    updateDraftLocally((current) => {
      const next = structuredClone(current);
      if (item.name.includes("工作台")) {
        if (!next.application_structure.workspaces.some((workspace) => workspace.name === "审批工作台")) {
          next.application_structure.workspaces.push({ id: createLocalId("workspace"), name: "审批工作台" });
        }
        if (!next.application_structure.pages.some((page) => page.name === "待办处理页")) {
          next.application_structure.pages.push({
            id: createLocalId("page"),
            name: "待办处理页",
            page_type: "task_form",
          });
        }
      }
      if (item.name.includes("进度")) {
        if (!next.application_structure.pages.some((page) => page.name === "办理进度页")) {
          next.application_structure.pages.push({
            id: createLocalId("page"),
            name: "办理进度页",
            page_type: "tracking",
          });
        }
      }
      if (item.name.includes("监控") || item.name.includes("统计")) {
        if (!next.application_structure.pages.some((page) => page.name === "业务监控页")) {
          next.application_structure.pages.push({
            id: createLocalId("page"),
            name: "业务监控页",
            page_type: "dashboard",
          });
        }
      }
      return next;
    });
  }

  function addAudienceManually() {
    if (!draft || !quickInputs.audienceName.trim()) {
      return;
    }
    const audienceName = quickInputs.audienceName.trim();
    updateDraftLocally((current) => ({
      ...current,
      audiences: [
        ...current.audiences,
        {
          id: createLocalId("audience"),
          name: audienceName,
          description: quickInputs.audienceDescription.trim(),
        },
      ],
      manual_additions: addManualAddition(current.manual_additions, "audience", audienceName),
    }));
    setQuickInputs((current) => ({ ...current, audienceName: "", audienceDescription: "" }));
  }

  function addRoleManually() {
    if (!draft || !quickInputs.roleName.trim()) {
      return;
    }
    const roleName = quickInputs.roleName.trim();
    const linkedAudienceId = draft.audiences[0]?.id ?? "";
    updateDraftLocally((current) => ({
      ...current,
      roles: [
        ...current.roles,
        {
          id: createLocalId("role"),
          name: roleName,
          audience_id: linkedAudienceId,
          responsibility_summary: quickInputs.roleSummary.trim(),
        },
      ],
      manual_additions: addManualAddition(current.manual_additions, "role", roleName),
    }));
    setQuickInputs((current) => ({ ...current, roleName: "", roleSummary: "" }));
  }

  function addFlowManually() {
    if (!quickInputs.flowName.trim()) {
      return;
    }
    const flowName = quickInputs.flowName.trim();
    updateDraftLocally((current) => ({
      ...current,
      business_flows: [
        ...current.business_flows,
        {
          id: createLocalId("flow"),
          name: flowName,
          scope: "core",
          priority: quickInputs.flowPriority,
          participants: current.roles.map((role) => role.id),
        },
      ],
      manual_additions: addManualAddition(current.manual_additions, "flow", flowName),
    }));
    setQuickInputs((current) => ({ ...current, flowName: "", flowPriority: "high" }));
  }

  function addObjectManually() {
    if (!quickInputs.objectName.trim()) {
      return;
    }
    const objectName = quickInputs.objectName.trim();
    updateDraftLocally((current) => ({
      ...current,
      business_objects: [
        ...current.business_objects,
        {
          id: createLocalId("object"),
          name: objectName,
          description: quickInputs.objectDescription.trim(),
        },
      ],
      manual_additions: addManualAddition(current.manual_additions, "object", objectName),
    }));
    setQuickInputs((current) => ({ ...current, objectName: "", objectDescription: "" }));
  }

  function addEventManually() {
    if (!quickInputs.eventName.trim()) {
      return;
    }
    const eventName = quickInputs.eventName.trim();
    updateDraftLocally((current) => ({
      ...current,
      key_events: [
        ...current.key_events,
        {
          id: createLocalId("event"),
          name: eventName,
          description: quickInputs.eventDescription.trim(),
        },
      ],
      manual_additions: addManualAddition(current.manual_additions, "event", eventName),
    }));
    setQuickInputs((current) => ({ ...current, eventName: "", eventDescription: "" }));
  }

  function addWorkspaceManually() {
    if (!quickInputs.workspaceName.trim()) {
      return;
    }
    const workspaceName = quickInputs.workspaceName.trim();
    updateDraftLocally((current) => ({
      ...current,
      application_structure: {
        ...current.application_structure,
        workspaces: [
          ...current.application_structure.workspaces,
          {
            id: createLocalId("workspace"),
            name: workspaceName,
          },
        ],
      },
      manual_additions: addManualAddition(current.manual_additions, "workspace", workspaceName),
    }));
    setQuickInputs((current) => ({ ...current, workspaceName: "" }));
  }

  function addPageManually() {
    if (!quickInputs.pageName.trim()) {
      return;
    }
    const pageName = quickInputs.pageName.trim();
    updateDraftLocally((current) => ({
      ...current,
      application_structure: {
        ...current.application_structure,
        pages: [
          ...current.application_structure.pages,
          {
            id: createLocalId("page"),
            name: pageName,
            page_type: quickInputs.pageType,
          },
        ],
      },
      manual_additions: addManualAddition(current.manual_additions, "page", pageName),
    }));
    setQuickInputs((current) => ({ ...current, pageName: "", pageType: "task_form" }));
  }

  async function handleSave() {
    if (!draft) {
      return;
    }

    try {
      setSaving(true);
      const response = await updateRequirementDraft(draft.draft_id, {
        current_step: draft.current_step,
        application_name: draft.application_name,
        application_goal: draft.application_goal,
        audiences: draft.audiences,
        roles: draft.roles,
        business_flows: draft.business_flows,
        business_objects: draft.business_objects,
        key_events: draft.key_events,
        application_structure: draft.application_structure,
        knowledge_references: draft.knowledge_references,
        manual_additions: draft.manual_additions,
      });
      setDraftState(response.data);
      setError(null);
      message.success("草稿已保存");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "保存草稿失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleComplete() {
    if (!draft) {
      return;
    }

    try {
      setCompleting(true);
      const response = await completeRequirementDraft(draft.draft_id);
      setDraftState(response.data);
      message.success("建模已完成");
    } catch (completeError) {
      setError(completeError instanceof Error ? completeError.message : "完成建模失败");
    } finally {
      setCompleting(false);
    }
  }

  async function handleExport() {
    if (!draft) {
      return;
    }

    try {
      setExportOpen(true);
      setExportLoading(true);
      const response = await exportRequirementDraft(draft.draft_id);
      setExportData(response.data);
      setExportError(null);
    } catch (loadError) {
      setExportError(loadError instanceof Error ? loadError.message : "导出结果失败");
    } finally {
      setExportLoading(false);
    }
  }

  if (loading) {
    return (
      <Space direction="vertical" size={8} style={{ display: "flex", padding: "36px 0" }}>
        <Spin />
        <Typography.Text type="secondary">正在准备应用建模草稿...</Typography.Text>
      </Space>
    );
  }

  if (error && !draft) {
    return <Alert type="error" message="应用建模器暂不可用" description={error} showIcon />;
  }

  if (!draft) {
    return <Empty description="请先在顶部选择一个知识库，再进入建模引导" />;
  }

  return (
    <>
      {error ? <Alert type="error" message="应用建模提示" description={error} showIcon style={{ marginBottom: 16 }} /> : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: screens.lg ? `240px minmax(0, 1fr) minmax(${rightColumnMinWidth}px, 0.9fr)` : "1fr",
          gap: 16,
          alignItems: "start",
        }}
      >
        <Card
          style={{
            borderRadius: 20,
            background: "linear-gradient(180deg, #fbfbf9 0%, #f5f4ef 100%)",
            border: "1px solid rgba(15, 23, 42, 0.08)",
          }}
          styles={{ body: { padding: 18 } }}
        >
          <Space direction="vertical" size={16} style={{ display: "flex" }}>
            <div>
              <Typography.Text type="secondary">建模步骤</Typography.Text>
              <Typography.Title level={5} style={{ marginTop: 6, marginBottom: 0 }}>
                先做业务建模，再进入后续构建
              </Typography.Title>
            </div>
            <Steps
              current={stepDefinitions.findIndex((item) => item.key === draft.current_step)}
              direction={screens.lg ? "vertical" : "horizontal"}
              items={stepDefinitions.map((item) => ({
                title: item.title,
                description: screens.lg ? item.question : undefined,
                onClick: () => changeStep(item.key),
              }))}
            />
          </Space>
        </Card>

        <Space direction="vertical" size={16} style={{ display: "flex" }}>
          <Card
            style={{
              borderRadius: 24,
              background:
                "linear-gradient(135deg, rgba(255,250,240,0.92) 0%, rgba(245,248,255,0.96) 55%, rgba(240,247,242,0.96) 100%)",
              border: "1px solid rgba(15, 23, 42, 0.06)",
            }}
            styles={{ body: { padding: 22 } }}
          >
            <Space direction="vertical" size={16} style={{ display: "flex" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
                <div>
                  <Tag color={draft.status === "completed" ? "green" : "blue"}>{draft.status === "completed" ? "已完成" : "草稿中"}</Tag>
                  <Typography.Title level={4} style={{ margin: "8px 0 4px" }}>
                    {currentStepDefinition.question}
                  </Typography.Title>
                  <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
                    {currentStepDefinition.hint}
                  </Typography.Paragraph>
                </div>
                <Space>
                  <Button onClick={() => void handleSave()} loading={saving}>
                    保存草稿
                  </Button>
                  <Button onClick={() => void handleComplete()} loading={completing}>
                    完成建模
                  </Button>
                  <Button type="primary" onClick={() => void handleExport()} loading={exportLoading}>
                    导出结果
                  </Button>
                </Space>
              </div>

              <Input
                size="large"
                placeholder="先给这个应用起个名字"
                value={draft.application_name}
                onChange={(event) =>
                  updateDraftLocally((current) => ({ ...current, application_name: event.target.value }))
                }
              />

              {draft.current_step === "goal" ? (
                <Space direction="vertical" size={16} style={{ display: "flex" }}>
                  <Space direction="vertical" size={12} style={{ display: "flex" }}>
                    <Input.TextArea
                      rows={4}
                      placeholder="请直白地描述当前业务中的痛点、低效点或不透明点"
                      value={draft.application_goal.problem_statement}
                      onChange={(event) =>
                        updateDraftLocally((current) => ({
                          ...current,
                          application_goal: { ...current.application_goal, problem_statement: event.target.value },
                        }))
                      }
                    />
                    <Input.TextArea
                      rows={3}
                      placeholder="希望通过这个应用实现什么结果"
                      value={draft.application_goal.target_outcome}
                      onChange={(event) =>
                        updateDraftLocally((current) => ({
                          ...current,
                          application_goal: { ...current.application_goal, target_outcome: event.target.value },
                        }))
                      }
                    />
                    <Input.TextArea
                      rows={3}
                      placeholder="成功标准，按换行输入，例如：审批时长下降"
                      value={draft.application_goal.success_criteria.join("\n")}
                      onChange={(event) =>
                        updateDraftLocally((current) => ({
                          ...current,
                          application_goal: {
                            ...current.application_goal,
                            success_criteria: event.target.value
                              .split("\n")
                              .map((item) => item.trim())
                              .filter(Boolean),
                          },
                        }))
                      }
                    />
                  </Space>
                  <RecommendationPanel
                    title="可以直接采用的业务目标建议"
                    items={draftState.recommendations.goal}
                    onApply={applyGoalRecommendation}
                  />
                </Space>
              ) : null}

              {draft.current_step === "audience" ? (
                <Space direction="vertical" size={16} style={{ display: "flex" }}>
                  <Card size="small" title="使用对象">
                    <Space direction="vertical" size={12} style={{ display: "flex" }}>
                      <Input
                        placeholder="例如：业务办理人员"
                        value={quickInputs.audienceName}
                        onChange={(event) => updateQuickInput("audienceName", event.target.value)}
                      />
                      <Input.TextArea
                        rows={2}
                        placeholder="他主要用这个应用做什么"
                        value={quickInputs.audienceDescription}
                        onChange={(event) => updateQuickInput("audienceDescription", event.target.value)}
                      />
                      <Button onClick={addAudienceManually}>加入使用对象</Button>
                      <List
                        size="small"
                        dataSource={draft.audiences}
                        locale={{ emptyText: "还没有定义使用对象" }}
                        renderItem={(item) => (
                          <List.Item>
                            <Space direction="vertical" size={2} style={{ display: "flex" }}>
                              <Typography.Text strong>{item.name}</Typography.Text>
                              <Typography.Text type="secondary">{item.description || "未补充说明"}</Typography.Text>
                            </Space>
                          </List.Item>
                        )}
                      />
                    </Space>
                  </Card>
                  <Card size="small" title="业务角色">
                    <Space direction="vertical" size={12} style={{ display: "flex" }}>
                      <Input
                        placeholder="例如：审核方"
                        value={quickInputs.roleName}
                        onChange={(event) => updateQuickInput("roleName", event.target.value)}
                      />
                      <Input.TextArea
                        rows={2}
                        placeholder="这个角色要承担什么职责"
                        value={quickInputs.roleSummary}
                        onChange={(event) => updateQuickInput("roleSummary", event.target.value)}
                      />
                      <Button onClick={addRoleManually}>加入业务角色</Button>
                      <List
                        size="small"
                        dataSource={draft.roles}
                        locale={{ emptyText: "还没有定义业务角色" }}
                        renderItem={(item) => (
                          <List.Item>
                            <Space direction="vertical" size={2} style={{ display: "flex" }}>
                              <Typography.Text strong>{item.name}</Typography.Text>
                              <Typography.Text type="secondary">
                                {item.responsibility_summary || "未补充职责说明"}
                              </Typography.Text>
                            </Space>
                          </List.Item>
                        )}
                      />
                    </Space>
                  </Card>
                  <RecommendationPanel
                    title="使用对象推荐"
                    items={draftState.recommendations.audience}
                    onApply={applyAudienceRecommendation}
                  />
                </Space>
              ) : null}

              {draft.current_step === "flow" ? (
                <Space direction="vertical" size={16} style={{ display: "flex" }}>
                  <Card size="small" title="核心流程范围">
                    <Space direction="vertical" size={12} style={{ display: "flex" }}>
                      <Input
                        placeholder="例如：申请审批流程"
                        value={quickInputs.flowName}
                        onChange={(event) => updateQuickInput("flowName", event.target.value)}
                      />
                      <Select
                        options={[
                          { value: "high", label: "优先级高" },
                          { value: "medium", label: "优先级中" },
                          { value: "low", label: "优先级低" },
                        ]}
                        value={quickInputs.flowPriority}
                        onChange={(value) => updateQuickInput("flowPriority", value)}
                      />
                      <Button onClick={addFlowManually}>加入核心流程</Button>
                      <List
                        size="small"
                        dataSource={draft.business_flows}
                        locale={{ emptyText: "还没有定义核心流程" }}
                        renderItem={(item) => (
                          <List.Item>
                            <Space style={{ width: "100%", justifyContent: "space-between" }}>
                              <Typography.Text>{item.name}</Typography.Text>
                              <Tag>{item.priority || "未定义优先级"}</Tag>
                            </Space>
                          </List.Item>
                        )}
                      />
                    </Space>
                  </Card>
                  <RecommendationPanel
                    title="流程推荐"
                    items={draftState.recommendations.flow}
                    onApply={applyFlowRecommendation}
                  />
                </Space>
              ) : null}

              {draft.current_step === "object_event" ? (
                <Space direction="vertical" size={16} style={{ display: "flex" }}>
                  <Card size="small" title="信息对象">
                    <Space direction="vertical" size={12} style={{ display: "flex" }}>
                      <Input
                        placeholder="例如：申请单"
                        value={quickInputs.objectName}
                        onChange={(event) => updateQuickInput("objectName", event.target.value)}
                      />
                      <Input.TextArea
                        rows={2}
                        placeholder="它是什么，为什么关键"
                        value={quickInputs.objectDescription}
                        onChange={(event) => updateQuickInput("objectDescription", event.target.value)}
                      />
                      <Button onClick={addObjectManually}>加入信息对象</Button>
                    </Space>
                  </Card>
                  <Card size="small" title="关键动作 / 关键事件">
                    <Space direction="vertical" size={12} style={{ display: "flex" }}>
                      <Input
                        placeholder="例如：提交申请"
                        value={quickInputs.eventName}
                        onChange={(event) => updateQuickInput("eventName", event.target.value)}
                      />
                      <Input.TextArea
                        rows={2}
                        placeholder="这个动作为什么关键"
                        value={quickInputs.eventDescription}
                        onChange={(event) => updateQuickInput("eventDescription", event.target.value)}
                      />
                      <Button onClick={addEventManually}>加入关键动作</Button>
                    </Space>
                  </Card>
                  <RecommendationPanel
                    title="来自知识仓的对象与动作"
                    items={draftState.recommendations.object_event}
                    onApply={applyObjectEventRecommendation}
                  />
                </Space>
              ) : null}

              {draft.current_step === "structure" ? (
                <Space direction="vertical" size={16} style={{ display: "flex" }}>
                  <Card size="small" title="工作空间">
                    <Space direction="vertical" size={12} style={{ display: "flex" }}>
                      <Input
                        placeholder="例如：审批工作台"
                        value={quickInputs.workspaceName}
                        onChange={(event) => updateQuickInput("workspaceName", event.target.value)}
                      />
                      <Button onClick={addWorkspaceManually}>加入工作空间</Button>
                    </Space>
                  </Card>
                  <Card size="small" title="页面建议">
                    <Space direction="vertical" size={12} style={{ display: "flex" }}>
                      <Input
                        placeholder="例如：待办处理页"
                        value={quickInputs.pageName}
                        onChange={(event) => updateQuickInput("pageName", event.target.value)}
                      />
                      <Select
                        options={pageTypeOptions}
                        value={quickInputs.pageType}
                        onChange={(value) => updateQuickInput("pageType", value)}
                      />
                      <Button onClick={addPageManually}>加入页面</Button>
                    </Space>
                  </Card>
                  <RecommendationPanel
                    title="承载方式建议"
                    items={draftState.recommendations.structure}
                    onApply={applyStructureRecommendation}
                  />
                </Space>
              ) : null}
            </Space>
          </Card>
        </Space>

        <Space direction="vertical" size={16} style={{ display: "flex" }}>
          <Card style={{ borderRadius: 20 }}>
            <Typography.Title level={5}>业务模型预览</Typography.Title>
            <Descriptions column={1} size="small" styles={{ label: { width: 92 } }}>
              <Descriptions.Item label="应用名称">{draft.application_name || "未命名"}</Descriptions.Item>
              <Descriptions.Item label="目标结果">
                {draft.application_goal.target_outcome || "尚未明确"}
              </Descriptions.Item>
              <Descriptions.Item label="对象数量">{draft.audiences.length} 类</Descriptions.Item>
              <Descriptions.Item label="流程数量">{draft.business_flows.length} 条</Descriptions.Item>
            </Descriptions>

            <Divider style={{ marginBlock: 14 }} />

            <PreviewList
              title="对象清单"
              items={draft.audiences.map((item) => `${item.name}${item.description ? ` · ${item.description}` : ""}`)}
            />
            <PreviewList
              title="流程清单"
              items={draft.business_flows.map((item) => `${item.name} · ${item.priority || "未设优先级"}`)}
            />
            <PreviewList
              title="信息对象 / 动作"
              items={[
                ...draft.business_objects.map((item) => `对象：${item.name}`),
                ...draft.key_events.map((item) => `动作：${item.name}`),
              ]}
            />
            <PreviewList
              title="领域流程候选"
              items={draftState.recommendations.flow.map((item) => item.name)}
            />
          </Card>

          <Card style={{ borderRadius: 20 }}>
            <Typography.Title level={5}>应用结构建议</Typography.Title>
            <PreviewList
              title="工作空间"
              items={draft.application_structure.workspaces.map((item) => item.name)}
            />
            <PreviewList
              title="页面建议"
              items={draft.application_structure.pages.map((item) => `${item.name} · ${item.page_type || "未定义"}`)}
            />
            <Divider style={{ marginBlock: 14 }} />
            <Typography.Text type="secondary">当前步骤可直接采用的建议</Typography.Text>
            <Space wrap size={[8, 8]} style={{ display: "flex", marginTop: 10 }}>
              {draftState.recommendations[draft.current_step].length > 0 ? (
                draftState.recommendations[draft.current_step].map((item) => (
                  <Tag key={item.id} style={{ paddingInline: 10, lineHeight: "28px", borderRadius: 999 }}>
                    {item.name}
                  </Tag>
                ))
              ) : (
                <Tag style={{ paddingInline: 10, lineHeight: "28px", borderRadius: 999 }}>暂无推荐</Tag>
              )}
            </Space>
          </Card>

          <Card style={{ borderRadius: 20 }}>
            <Typography.Title level={5}>结构化输出</Typography.Title>
            <Typography.Paragraph type="secondary">
              当前阶段的权威产物是结构化需求模型，可直接导出为 JSON / YAML / Markdown。
            </Typography.Paragraph>
            <pre
              style={{
                margin: 0,
                padding: 14,
                background: "#f7f7f5",
                borderRadius: 14,
                fontSize: 12,
                lineHeight: 1.6,
                overflowX: "auto",
                whiteSpace: "pre-wrap",
              }}
            >
              {JSON.stringify(
                {
                  application_name: draft.application_name,
                  current_step: draft.current_step,
                  audiences: draft.audiences.map((item) => item.name),
                  business_flows: draft.business_flows.map((item) => item.name),
                  business_objects: draft.business_objects.map((item) => item.name),
                  key_events: draft.key_events.map((item) => item.name),
                  pages: draft.application_structure.pages.map((item) => item.name),
                },
                null,
                2,
              )}
            </pre>
          </Card>
        </Space>
      </div>

      <ValidationDrawer
        title="导出结果预览"
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        width={760}
        loading={exportLoading}
        loadingText="正在生成导出结果..."
        error={exportError}
        errorMessage="导出结果暂不可用"
      >
        {exportData ? (
          <Space direction="vertical" size={16} style={{ display: "flex" }}>
            <Card size="small" title="Markdown">
              <Space direction="vertical" size={4} style={{ display: "flex" }}>
                {exportData.markdown.split("\n").map((line, index) => (
                  <Typography.Text key={`${line}-${index}`} style={{ whiteSpace: "pre-wrap" }}>
                    {line || " "}
                  </Typography.Text>
                ))}
              </Space>
            </Card>
            <Card size="small" title="JSON">
              <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{exportData.json_text}</pre>
            </Card>
            <Card size="small" title="YAML">
              <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{exportData.yaml_text}</pre>
            </Card>
          </Space>
        ) : null}
      </ValidationDrawer>
    </>
  );
}

function RecommendationPanel({
  title,
  items,
  onApply,
}: {
  title: string;
  items: RequirementRecommendation[];
  onApply: (item: RequirementRecommendation) => void;
}) {
  return (
    <Card size="small" title={title}>
      <List
        dataSource={items}
        locale={{ emptyText: "当前没有可用建议" }}
        renderItem={(item) => (
          <List.Item
            actions={[
              <Button key={`${item.id}-apply`} type="link" onClick={() => onApply(item)}>
                采用
              </Button>,
            ]}
          >
            <Space direction="vertical" size={6} style={{ display: "flex", width: "100%" }}>
              <Space wrap size={[8, 8]}>
                <Typography.Text strong>{item.name}</Typography.Text>
                <Tag color={item.source === "recommended_domain" ? "gold" : "blue"}>
                  {sourceLabels[item.source]}
                </Tag>
              </Space>
              <Typography.Text type="secondary">{item.description}</Typography.Text>
              {item.tags.length > 0 ? (
                <Space wrap size={[6, 6]}>
                  {item.tags.map((tag) => (
                    <Tag key={`${item.id}-${tag}`}>{tag}</Tag>
                  ))}
                </Space>
              ) : null}
            </Space>
          </List.Item>
        )}
      />
    </Card>
  );
}

function PreviewList({ title, items }: { title: string; items: string[] }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <Typography.Text type="secondary">{title}</Typography.Text>
      {items.length > 0 ? (
        <List
          size="small"
          dataSource={items}
          renderItem={(item) => (
            <List.Item style={{ paddingInline: 0 }}>
              <Typography.Text>{item}</Typography.Text>
            </List.Item>
          )}
        />
      ) : (
        <Typography.Paragraph type="secondary" style={{ marginTop: 6, marginBottom: 0 }}>
          暂无内容
        </Typography.Paragraph>
      )}
    </div>
  );
}
