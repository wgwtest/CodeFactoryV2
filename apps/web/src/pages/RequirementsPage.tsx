import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Form,
  Input,
  List,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";

import { ValidationWorkspace } from "../components/ValidationWorkspace";
import { useArchiveContext } from "../context/ArchiveContext";
import type {
  RequirementFormalElement,
  RequirementObject,
  RequirementSpecDetail,
  RequirementSpecPayload,
  RequirementSpecSummary,
  RequirementSpecWriteInput,
} from "../lib/api";
import {
  createRequirementSpec,
  getRequirementFormalElements,
  getRequirementSpec,
  getRequirementSpecs,
  updateRequirementSpec,
} from "../lib/requirements";

function createLocalId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Math.random().toString(16).slice(2)}`;
}

function buildEmptyPayload(): RequirementSpecPayload {
  return {
    application: {
      name: "未命名应用",
      domain: "",
      summary: "",
      target_users: [],
    },
    objects: [],
    processes: [],
    rules: [],
    metrics: [],
    non_functional_constraints: [],
  };
}

function toWriteInput(detail: RequirementSpecDetail): RequirementSpecWriteInput {
  return {
    archive_id: detail.archive_id,
    status: (detail.status as "draft" | "reviewing" | "ready") ?? "draft",
    payload: detail.payload,
  };
}

function toSummary(detail: RequirementSpecDetail): RequirementSpecSummary {
  return {
    id: detail.id,
    application_name: detail.application_name,
    domain_name: detail.domain_name,
    status: detail.status,
    archive_id: detail.archive_id,
    object_count: detail.object_count,
    formal_object_count: detail.formal_object_count,
    temporary_object_count: detail.temporary_object_count,
    process_count: detail.process_count,
    updated_at: detail.updated_at,
  };
}

export function RequirementsPage() {
  const { activeArchive, activeArchiveId } = useArchiveContext();
  const [specs, setSpecs] = useState<RequirementSpecSummary[]>([]);
  const [currentSpec, setCurrentSpec] = useState<RequirementSpecDetail | null>(null);
  const [formalElements, setFormalElements] = useState<RequirementFormalElement[]>([]);
  const [searchValue, setSearchValue] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [tempName, setTempName] = useState("");
  const [tempDescription, setTempDescription] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const specsPromise = getRequirementSpecs();
        const formalElementsPromise = activeArchiveId
          ? getRequirementFormalElements("entity", activeArchiveId)
          : Promise.resolve({ data: [] as RequirementFormalElement[] });
        const [specsResponse, formalElementsResponse] = await Promise.all([specsPromise, formalElementsPromise]);
        if (cancelled) {
          return;
        }
        setSpecs(specsResponse.data);
        setFormalElements(formalElementsResponse.data);
        setError(null);

        if (specsResponse.data.length > 0) {
          const detailResponse = await getRequirementSpec(specsResponse.data[0].id);
          if (!cancelled) {
            setCurrentSpec(detailResponse.data);
          }
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载需求建模数据失败");
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
  }, [activeArchiveId]);

  const filteredFormalElements = useMemo(() => {
    const normalizedQuery = searchValue.trim().toLowerCase();
    if (!normalizedQuery) {
      return formalElements;
    }
    return formalElements.filter((item) =>
      [item.name, ...item.aliases].join(" ").toLowerCase().includes(normalizedQuery),
    );
  }, [formalElements, searchValue]);

  const liveCounts = useMemo(() => {
    const objects = currentSpec?.payload.objects ?? [];
    const formalObjectCount = objects.filter((item) => item.source_kind === "formal").length;
    return {
      formalObjectCount,
      temporaryObjectCount: objects.length - formalObjectCount,
      processCount: currentSpec?.payload.processes.length ?? 0,
    };
  }, [currentSpec]);

  async function handleOpenSpec(specId: string) {
    try {
      const response = await getRequirementSpec(specId);
      setCurrentSpec(response.data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载需求模型失败");
    }
  }

  async function handleCreateSpec() {
    try {
      setCreating(true);
      const response = await createRequirementSpec({
        archive_id: activeArchiveId ?? undefined,
        status: "draft",
        payload: buildEmptyPayload(),
      });
      setCurrentSpec(response.data);
      setSpecs((current) => [toSummary(response.data), ...current.filter((item) => item.id !== response.data.id)]);
      setError(null);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "创建需求模型失败");
    } finally {
      setCreating(false);
    }
  }

  async function handleSave() {
    if (!currentSpec) {
      return;
    }

    try {
      setSaving(true);
      const response = await updateRequirementSpec(currentSpec.id, toWriteInput(currentSpec));
      setCurrentSpec(response.data);
      setSpecs((current) => [toSummary(response.data), ...current.filter((item) => item.id !== response.data.id)]);
      setError(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "保存需求模型失败");
    } finally {
      setSaving(false);
    }
  }

  function updateApplication<K extends keyof RequirementSpecPayload["application"]>(
    key: K,
    value: RequirementSpecPayload["application"][K],
  ) {
    setCurrentSpec((current) =>
      current
        ? {
            ...current,
            payload: {
              ...current.payload,
              application: {
                ...current.payload.application,
                [key]: value,
              },
            },
          }
        : current,
    );
  }

  function addFormalElement(element: RequirementFormalElement) {
    setCurrentSpec((current) => {
      if (!current) {
        return current;
      }

      const alreadyExists = current.payload.objects.some((item) => item.source_item_id === element.id);
      if (alreadyExists) {
        return current;
      }

      const nextObject: RequirementObject = {
        id: `formal-${element.id}`,
        name: element.name,
        object_kind: "business",
        source_kind: "formal",
        category: element.category,
        aliases: element.aliases,
        summary: element.summary,
        description: element.summary,
        source_archive_id: element.source_archive_id,
        source_item_type: element.item_type,
        source_item_id: element.id,
      };

      return {
        ...current,
        payload: {
          ...current.payload,
          objects: [...current.payload.objects, nextObject],
        },
      };
    });
  }

  function updateObjectKind(objectId: string, objectKind: "business" | "supporting") {
    setCurrentSpec((current) =>
      current
        ? {
            ...current,
            payload: {
              ...current.payload,
              objects: current.payload.objects.map((item) =>
                item.id === objectId ? { ...item, object_kind: objectKind } : item,
              ),
            },
          }
        : current,
    );
  }

  function removeObject(objectId: string) {
    setCurrentSpec((current) =>
      current
        ? {
            ...current,
            payload: {
              ...current.payload,
              objects: current.payload.objects.filter((item) => item.id !== objectId),
            },
          }
        : current,
    );
  }

  function handleAddTemporaryObject() {
    const normalizedName = tempName.trim();
    if (!normalizedName) {
      return;
    }

    setCurrentSpec((current) =>
      current
        ? {
            ...current,
            payload: {
              ...current.payload,
              objects: [
                ...current.payload.objects,
                {
                  id: createLocalId("temporary-object"),
                  name: normalizedName,
                  object_kind: "supporting",
                  source_kind: "temporary",
                  category: "domain_concept",
                  aliases: [],
                  summary: tempDescription.trim() || "建模现场新增的临时对象。",
                  description: tempDescription.trim() || null,
                  source_archive_id: null,
                  source_item_type: null,
                  source_item_id: null,
                },
              ],
            },
          }
        : current,
    );
    setTempName("");
    setTempDescription("");
    setModalOpen(false);
  }

  return (
    <ValidationWorkspace
      title="应用需求建模"
      description={`先围绕业务对象和支撑对象建立结构化需求模型，正式元素来自已发布知识仓，临时元素允许现场补充但不会阻塞建模。${activeArchive ? ` 当前知识库：${activeArchive.name}。` : ""}`}
      actions={
        <Space>
          <Button type="primary" onClick={handleCreateSpec} loading={creating}>
            创建需求模型
          </Button>
          <Button onClick={handleSave} disabled={!currentSpec} loading={saving}>
            保存模型
          </Button>
        </Space>
      }
      stats={[
        { title: "模型数", value: specs.length },
        { title: "正式对象", value: liveCounts.formalObjectCount },
        { title: "临时对象", value: liveCounts.temporaryObjectCount },
        { title: "流程", value: liveCounts.processCount },
      ]}
    >
      {error ? <Alert type="error" showIcon message="需求建模暂不可用" description={error} /> : null}

      <Row gutter={24} align="top">
        <Col xs={24} lg={7}>
          <Card title="需求模型列表" loading={loading}>
            {specs.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="还没有需求模型，可以先创建一个草稿。"
              />
            ) : (
              <List
                dataSource={specs}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Button key="open" type={currentSpec?.id === item.id ? "primary" : "default"} onClick={() => handleOpenSpec(item.id)}>
                        打开
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={item.application_name}
                      description={
                        <Space direction="vertical" size={4}>
                          <Typography.Text type="secondary">{item.domain_name || "未设置领域范围"}</Typography.Text>
                          <Space size={8} wrap>
                            <Tag color="blue">正式 {item.formal_object_count}</Tag>
                            <Tag color="orange">临时 {item.temporary_object_count}</Tag>
                          </Space>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={17}>
          {!currentSpec ? (
            <Card>
              <Empty
                description="先创建或打开一个需求模型，再开始围绕对象进行建模。"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            </Card>
          ) : (
            <Space direction="vertical" size={24} style={{ display: "flex" }}>
              <Card title="应用基本信息">
                <Form layout="vertical">
                  <Form.Item label="应用名称">
                    <Input
                      aria-label="应用名称"
                      value={currentSpec.payload.application.name}
                      onChange={(event) => updateApplication("name", event.target.value)}
                    />
                  </Form.Item>
                  <Form.Item label="领域范围">
                    <Input
                      aria-label="领域范围"
                      value={currentSpec.payload.application.domain}
                      onChange={(event) => updateApplication("domain", event.target.value)}
                    />
                  </Form.Item>
                  <Form.Item label="目标用户">
                    <Input
                      aria-label="目标用户"
                      value={currentSpec.payload.application.target_users.join(",")}
                      onChange={(event) =>
                        updateApplication(
                          "target_users",
                          event.target.value
                            .split(/[，,]/)
                            .map((item) => item.trim())
                            .filter(Boolean),
                        )
                      }
                    />
                  </Form.Item>
                  <Form.Item label="需求摘要">
                    <Input.TextArea
                      aria-label="需求摘要"
                      rows={4}
                      value={currentSpec.payload.application.summary}
                      onChange={(event) => updateApplication("summary", event.target.value)}
                    />
                  </Form.Item>
                </Form>
                <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
                  最近保存时间：{currentSpec.updated_at}
                </Typography.Paragraph>
              </Card>

              <Card
                title="正式领域对象"
                extra={
                  <Input
                    aria-label="搜索正式对象"
                    placeholder="搜索正式对象或别名"
                    value={searchValue}
                    onChange={(event) => setSearchValue(event.target.value)}
                    style={{ width: 260 }}
                  />
                }
              >
                <List
                  dataSource={filteredFormalElements}
                  locale={{ emptyText: "暂无可用正式元素" }}
                  renderItem={(item) => (
                    <List.Item
                      actions={[
                        <Button key="add" onClick={() => addFormalElement(item)}>
                          加入模型
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={
                          <Space size={8} wrap>
                            <span>{item.name}</span>
                            <Tag>{item.category ?? "未分类"}</Tag>
                            <Tag color="blue">{item.document_count} 文档</Tag>
                          </Space>
                        }
                        description={
                          <Space direction="vertical" size={4}>
                            <Typography.Text type="secondary">{item.summary}</Typography.Text>
                            {item.aliases.length > 0 ? (
                              <Typography.Text type="secondary">别名：{item.aliases.join("、")}</Typography.Text>
                            ) : null}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              </Card>

              <Card
                title="已选业务对象"
                extra={
                  <Button onClick={() => setModalOpen(true)}>
                    新增临时对象
                  </Button>
                }
              >
                <Table
                  rowKey="id"
                  pagination={false}
                  dataSource={currentSpec.payload.objects}
                  locale={{ emptyText: "还没有加入对象，可以从正式元素选择或新增临时对象。" }}
                  columns={[
                    {
                      title: "名称",
                      dataIndex: "name",
                    },
                    {
                      title: "对象类型",
                      render: (_value: unknown, record: RequirementObject) => (
                        <Select
                          value={record.object_kind}
                          style={{ width: 120 }}
                          options={[
                            { label: "业务对象", value: "business" },
                            { label: "支撑对象", value: "supporting" },
                          ]}
                          onChange={(value) => updateObjectKind(record.id, value)}
                        />
                      ),
                    },
                    {
                      title: "来源",
                      render: (_value: unknown, record: RequirementObject) =>
                        record.source_kind === "formal" ? <Tag color="blue">正式元素</Tag> : <Tag color="orange">临时元素</Tag>,
                    },
                    {
                      title: "说明",
                      render: (_value: unknown, record: RequirementObject) => record.description || record.summary || "-",
                    },
                    {
                      title: "操作",
                      render: (_value: unknown, record: RequirementObject) => (
                        <Button danger type="link" onClick={() => removeObject(record.id)}>
                          移除
                        </Button>
                      ),
                    },
                  ]}
                />
              </Card>
            </Space>
          )}
        </Col>
      </Row>

      <Modal
        title="新增临时对象"
        open={modalOpen}
        okText="确认添加"
        cancelText="取消"
        onCancel={() => setModalOpen(false)}
        onOk={handleAddTemporaryObject}
      >
        <Form layout="vertical">
          <Form.Item label="对象名称">
            <Input
              aria-label="对象名称"
              value={tempName}
              onChange={(event) => setTempName(event.target.value)}
            />
          </Form.Item>
          <Form.Item label="对象说明">
            <Input.TextArea
              aria-label="对象说明"
              rows={4}
              value={tempDescription}
              onChange={(event) => setTempDescription(event.target.value)}
            />
          </Form.Item>
        </Form>
      </Modal>
    </ValidationWorkspace>
  );
}
