import { useEffect, useMemo, useState } from "react";

import { Alert, Card, Col, Descriptions, Empty, List, Row, Space, Spin, Statistic, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";

import type {
  ArchiveKnowledgeEdge,
  ArchiveKnowledgeGraph,
  ArchiveKnowledgeItemDetail,
  ArchiveKnowledgeNode,
  ArchiveKnowledgeSummary,
  ArchivePublicationOverview,
} from "../../../../lib/api";
import { PageFrame } from "../../common/PageFrame";
import type { P1ModulePageProps } from "../../types";
import { knowledgeResultsApi } from "./api";
import type { KnowledgeGraphMode, KnowledgeRelationRow, KnowledgeResultKind, KnowledgeResultRow } from "./types";

type LoadState = {
  summary: ArchiveKnowledgeSummary | null;
  graph: ArchiveKnowledgeGraph | null;
  publication: ArchivePublicationOverview | null;
  rows: KnowledgeResultRow[];
  selectedObjectId: string | null;
  selectedRelationId: string | null;
  visibleGraphMode: KnowledgeGraphMode;
  selectedDetail: ArchiveKnowledgeItemDetail | null;
  loading: boolean;
  detailLoading: boolean;
  error: string | null;
};

const emptyState: LoadState = {
  summary: null,
  graph: null,
  publication: null,
  rows: [],
  selectedObjectId: null,
  selectedRelationId: null,
  visibleGraphMode: "semantic_cluster",
  selectedDetail: null,
  loading: true,
  detailLoading: false,
  error: null,
};

const kindMeta: Record<KnowledgeResultKind, { label: string; color: string }> = {
  entity: { label: "实体", color: "blue" },
  event: { label: "事件", color: "orange" },
  process: { label: "流程", color: "green" },
  graph_node: { label: "图谱节点", color: "purple" },
};

const graphKindMeta: Record<KnowledgeResultKind, { label: string; className: string }> = {
  entity: { label: "实体", className: "entity" },
  event: { label: "事件", className: "event" },
  process: { label: "流程", className: "process" },
  graph_node: { label: "图谱节点", className: "graph-node" },
};

const GRAPH_NODE_LIMIT = 24;
const GRAPH_WIDTH = 1040;
const GRAPH_HEIGHT = 520;
const GRAPH_NODE_WIDTH = 154;
const GRAPH_NODE_HEIGHT = 62;

function readErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function firstText(...values: Array<string | null | undefined>) {
  return values.find((value) => value && value.trim().length > 0) ?? "";
}

function buildRelationId(edge: ArchiveKnowledgeEdge, index: number) {
  return `${edge.source}::${edge.label}::${edge.target}::${index}`;
}

function buildRows(
  entities: Awaited<ReturnType<typeof knowledgeResultsApi.getArchiveEntities>>["data"],
  events: Awaited<ReturnType<typeof knowledgeResultsApi.getArchiveEvents>>["data"],
  processes: Awaited<ReturnType<typeof knowledgeResultsApi.getArchiveProcesses>>["data"],
  graph: ArchiveKnowledgeGraph,
): KnowledgeResultRow[] {
  const rows: KnowledgeResultRow[] = [
    ...entities.map((item) => ({
      id: item.id,
      name: firstText(item.language_projection?.display_name_zh, item.interpretation.display_name, item.name),
      kind: "entity" as const,
      kindLabel: "实体",
      category: item.category,
      documentCount: item.document_count,
      summary: firstText(item.language_projection?.description_zh, item.interpretation.summary),
      aliases: item.aliases,
    })),
    ...events.map((item) => ({
      id: item.id,
      name: firstText(item.language_projection?.display_name_zh, item.interpretation.display_name, item.name),
      kind: "event" as const,
      kindLabel: "事件",
      category: item.category,
      documentCount: item.document_count,
      summary: firstText(item.language_projection?.description_zh, item.interpretation.summary),
      aliases: item.aliases,
    })),
    ...processes.map((item) => ({
      id: item.id,
      name: firstText(item.language_projection?.display_name_zh, item.interpretation.display_name, item.name),
      kind: "process" as const,
      kindLabel: "流程",
      category: item.category,
      documentCount: item.document_count,
      summary: firstText(item.language_projection?.description_zh, item.interpretation.summary),
      aliases: item.aliases,
    })),
  ];

  const knownIds = new Set(rows.map((item) => item.id));
  for (const node of graph.nodes) {
    if (knownIds.has(node.id)) {
      continue;
    }
    rows.push({
      id: node.id,
      name: node.label,
      kind: "graph_node",
      kindLabel: "图谱节点",
      category: node.type || node.item_type,
      documentCount: node.document_count,
      summary: "该对象来自图谱节点投影，详情取决于后端是否已生成标准知识对象。",
      aliases: [],
    });
  }

  return rows;
}

type KnowledgeGraphRenderNode = {
  id: string;
  label: string;
  kind: KnowledgeResultKind;
  kindLabel: string;
  documentCount: number;
  x: number;
  y: number;
};

type KnowledgeGraphRenderEdge = ArchiveKnowledgeEdge & {
  id: string;
  active: boolean;
};

function resolveGraphNodeKind(node: ArchiveKnowledgeNode, rowById: Map<string, KnowledgeResultRow>): KnowledgeResultKind {
  const rowKind = rowById.get(node.id)?.kind;
  if (rowKind) {
    return rowKind;
  }
  if (node.item_type === "entity" || node.item_type === "event" || node.item_type === "process") {
    return node.item_type;
  }
  return "graph_node";
}

function resolveGraphNodeLabel(node: ArchiveKnowledgeNode, rowById: Map<string, KnowledgeResultRow>) {
  return firstText(rowById.get(node.id)?.name, node.label, node.id);
}

function getGraphNodeDegree(graph: ArchiveKnowledgeGraph) {
  const degreeById = new Map<string, number>();
  for (const edge of graph.edges) {
    degreeById.set(edge.source, (degreeById.get(edge.source) ?? 0) + 1);
    degreeById.set(edge.target, (degreeById.get(edge.target) ?? 0) + 1);
  }
  return degreeById;
}

function pickGraphNodeIds(graph: ArchiveKnowledgeGraph, selectedObjectId: string | null, visibleGraphMode: KnowledgeGraphMode) {
  const nodeIds = graph.nodes.map((node) => node.id);
  const nodeSet = new Set(nodeIds);
  const selectedGraphId = selectedObjectId && nodeSet.has(selectedObjectId) ? selectedObjectId : null;

  if (!selectedGraphId || visibleGraphMode === "semantic_cluster") {
    const degreeById = getGraphNodeDegree(graph);
    return graph.nodes
      .slice()
      .sort((left, right) => {
        const degreeDiff = (degreeById.get(right.id) ?? 0) - (degreeById.get(left.id) ?? 0);
        if (degreeDiff !== 0) {
          return degreeDiff;
        }
        return right.document_count - left.document_count;
      })
      .map((node) => node.id)
      .slice(0, GRAPH_NODE_LIMIT);
  }

  const neighborIds = graph.edges
    .flatMap((edge) => {
      if (edge.source === selectedGraphId) return [edge.target];
      if (edge.target === selectedGraphId) return [edge.source];
      return [];
    })
    .filter((id) => nodeSet.has(id));
  const ordered = [selectedGraphId, ...neighborIds, ...nodeIds.filter((id) => id !== selectedGraphId && !neighborIds.includes(id))];
  return Array.from(new Set(ordered)).slice(0, GRAPH_NODE_LIMIT);
}

function placeOnRing(
  nodes: KnowledgeGraphRenderNode[],
  centerX: number,
  centerY: number,
  radiusX: number,
  radiusY: number,
  startAngle = -Math.PI / 2,
) {
  nodes.forEach((node, index) => {
    const angle = startAngle + (2 * Math.PI * index) / Math.max(nodes.length, 1);
    node.x = centerX + Math.cos(angle) * radiusX - GRAPH_NODE_WIDTH / 2;
    node.y = centerY + Math.sin(angle) * radiusY - GRAPH_NODE_HEIGHT / 2;
  });
}

function placeInSemanticColumns(nodes: KnowledgeGraphRenderNode[]) {
  const columnX: Record<KnowledgeResultKind, number> = {
    entity: 78,
    process: 320,
    event: 562,
    graph_node: 804,
  };
  const grouped = nodes.reduce<Record<KnowledgeResultKind, KnowledgeGraphRenderNode[]>>(
    (accumulator, node) => {
      accumulator[node.kind].push(node);
      return accumulator;
    },
    { entity: [], process: [], event: [], graph_node: [] },
  );

  (Object.keys(grouped) as KnowledgeResultKind[]).forEach((kind) => {
    const group = grouped[kind];
    const gap = Math.min(92, 360 / Math.max(group.length - 1, 1));
    const totalHeight = gap * Math.max(group.length - 1, 0) + GRAPH_NODE_HEIGHT;
    const startY = Math.max(38, GRAPH_HEIGHT / 2 - totalHeight / 2);
    group.forEach((node, index) => {
      node.x = columnX[kind];
      node.y = startY + index * gap;
    });
  });
}

function buildGraphPreview(
  graph: ArchiveKnowledgeGraph | null,
  rows: KnowledgeResultRow[],
  selectedObjectId: string | null,
  visibleGraphMode: KnowledgeGraphMode,
) {
  if (!graph || graph.nodes.length === 0) {
    return { nodes: [], edges: [], truncated: false, totalNodes: 0 };
  }

  const rowById = new Map(rows.map((row) => [row.id, row]));
  const graphNodeById = new Map(graph.nodes.map((node) => [node.id, node]));
  const pickedIds = pickGraphNodeIds(graph, selectedObjectId, visibleGraphMode);
  const pickedIdSet = new Set(pickedIds);
  const selectedGraphId = selectedObjectId && pickedIdSet.has(selectedObjectId) ? selectedObjectId : null;
  const nodes = pickedIds
    .map((id) => graphNodeById.get(id))
    .filter((node): node is ArchiveKnowledgeNode => Boolean(node))
    .map((node) => {
      const kind = resolveGraphNodeKind(node, rowById);
      return {
        id: node.id,
        label: resolveGraphNodeLabel(node, rowById),
        kind,
        kindLabel: graphKindMeta[kind].label,
        documentCount: node.document_count,
        x: 0,
        y: 0,
      };
    });

  if (selectedGraphId && visibleGraphMode === "focus_neighborhood") {
    const selectedNode = nodes.find((node) => node.id === selectedGraphId);
    if (selectedNode) {
      selectedNode.x = GRAPH_WIDTH / 2 - GRAPH_NODE_WIDTH / 2;
      selectedNode.y = GRAPH_HEIGHT / 2 - GRAPH_NODE_HEIGHT / 2;
    }
    const directIds = new Set(
      graph.edges.flatMap((edge) => {
        if (edge.source === selectedGraphId && pickedIdSet.has(edge.target)) return [edge.target];
        if (edge.target === selectedGraphId && pickedIdSet.has(edge.source)) return [edge.source];
        return [];
      }),
    );
    placeOnRing(
      nodes.filter((node) => directIds.has(node.id)),
      GRAPH_WIDTH / 2,
      GRAPH_HEIGHT / 2,
      322,
      168,
    );
    placeOnRing(
      nodes.filter((node) => node.id !== selectedGraphId && !directIds.has(node.id)),
      GRAPH_WIDTH / 2,
      GRAPH_HEIGHT / 2,
      452,
      224,
      -Math.PI / 5,
    );
  } else {
    placeInSemanticColumns(nodes);
  }

  const edges: KnowledgeGraphRenderEdge[] = graph.edges
    .map((edge, index) => ({
      ...edge,
      id: buildRelationId(edge, index),
      active: Boolean(
        selectedGraphId &&
          visibleGraphMode === "focus_neighborhood" &&
          (edge.source === selectedGraphId || edge.target === selectedGraphId),
      ),
    }))
    .filter((edge) => pickedIdSet.has(edge.source) && pickedIdSet.has(edge.target));

  return {
    nodes,
    edges,
    truncated: graph.nodes.length > pickedIds.length,
    totalNodes: graph.nodes.length,
  };
}

function KnowledgeGraphPreview({
  graph,
  rows,
  selectedObjectId,
  selectedRelationId,
  visibleGraphMode,
  onSelect,
  onSelectRelation,
}: {
  graph: ArchiveKnowledgeGraph | null;
  rows: KnowledgeResultRow[];
  selectedObjectId: string | null;
  selectedRelationId: string | null;
  visibleGraphMode: KnowledgeGraphMode;
  onSelect: (id: string) => void;
  onSelectRelation: (relationId: string, sourceId: string) => void;
}) {
  const preview = buildGraphPreview(graph, rows, selectedObjectId, visibleGraphMode);
  const nodeById = new Map(preview.nodes.map((node) => [node.id, node]));

  if (preview.nodes.length === 0) {
    return <Empty description="暂无知识图谱，请先完成资料接入、抽取运行和知识生成。" />;
  }

  return (
    <Space direction="vertical" size={12} className="p1-results-graph">
      <Space wrap>
        <Tag color="blue">节点 {preview.nodes.length} / {preview.totalNodes}</Tag>
        <Tag color="geekblue">关系 {preview.edges.length}</Tag>
        {visibleGraphMode === "focus_neighborhood" ? <Tag color="gold">已按选中对象聚焦邻域</Tag> : <Tag>默认语义聚合视图</Tag>}
        {preview.truncated ? <Tag color="orange">节点较多，已截取可读范围</Tag> : null}
      </Space>
      <div className="p1-results-graph-canvas">
        <svg viewBox={`0 0 ${GRAPH_WIDTH} ${GRAPH_HEIGHT}`} role="img" aria-label="知识成果图谱">
          <defs>
            <marker id="p1-results-graph-arrow" markerHeight="8" markerWidth="8" orient="auto" refX="7" refY="4">
              <path d="M0,0 L8,4 L0,8 Z" fill="#94a3b8" />
            </marker>
          </defs>
          {preview.edges.map((edge) => {
            const source = nodeById.get(edge.source);
            const target = nodeById.get(edge.target);
            if (!source || !target) {
              return null;
            }
            const x1 = source.x + GRAPH_NODE_WIDTH / 2;
            const y1 = source.y + GRAPH_NODE_HEIGHT / 2;
            const x2 = target.x + GRAPH_NODE_WIDTH / 2;
            const y2 = target.y + GRAPH_NODE_HEIGHT / 2;
            return (
              <g
                key={edge.id}
                className={`${edge.active ? "is-active" : ""} ${edge.id === selectedRelationId ? "is-selected-relation" : ""}`}
                role="button"
                tabIndex={0}
                onClick={() => onSelectRelation(edge.id, edge.source)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    onSelectRelation(edge.id, edge.source);
                  }
                }}
              >
                <line
                  className="p1-results-graph-edge"
                  x1={x1}
                  x2={x2}
                  y1={y1}
                  y2={y2}
                  markerEnd="url(#p1-results-graph-arrow)"
                />
                <text className="p1-results-graph-edge-label" x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 6}>
                  {edge.label}
                </text>
              </g>
            );
          })}
          {preview.nodes.map((node) => (
            <foreignObject
              key={node.id}
              className="p1-results-graph-node-wrapper"
              height={GRAPH_NODE_HEIGHT}
              width={GRAPH_NODE_WIDTH}
              x={node.x}
              y={node.y}
            >
              <button
                className={`p1-results-graph-node ${graphKindMeta[node.kind].className} ${node.id === selectedObjectId ? "is-selected" : ""}`}
                title={node.label}
                type="button"
                onClick={() => onSelect(node.id)}
              >
                <span>{node.kindLabel} · {node.documentCount} 文档</span>
                <strong>{node.label}</strong>
              </button>
            </foreignObject>
          ))}
        </svg>
      </div>
    </Space>
  );
}

export function KnowledgeResultsPage({ context }: P1ModulePageProps) {
  const [state, setState] = useState<LoadState>(emptyState);

  useEffect(() => {
    let alive = true;
    setState((previous) => ({ ...previous, loading: true, error: null }));

    Promise.all([
      knowledgeResultsApi.getArchiveSummary(context.archiveId),
      knowledgeResultsApi.getArchiveGraph(context.archiveId),
      knowledgeResultsApi.getArchiveEntities(context.archiveId),
      knowledgeResultsApi.getArchiveEvents(context.archiveId),
      knowledgeResultsApi.getArchiveProcesses(context.archiveId),
      knowledgeResultsApi.getArchivePublication(context.archiveId),
    ])
      .then(([summaryResponse, graphResponse, entitiesResponse, eventsResponse, processesResponse, publicationResponse]) => {
        if (!alive) {
          return;
        }
        const rows = buildRows(entitiesResponse.data, eventsResponse.data, processesResponse.data, graphResponse.data);
        setState((previous) => ({
          ...previous,
          summary: summaryResponse.data,
          graph: graphResponse.data,
          publication: publicationResponse.data,
          rows,
          selectedObjectId: previous.selectedObjectId ?? rows[0]?.id ?? null,
          selectedRelationId: null,
          visibleGraphMode: "semantic_cluster",
          selectedDetail: null,
          loading: false,
          error: null,
        }));
      })
      .catch((error: unknown) => {
        if (!alive) {
          return;
        }
        setState((previous) => ({
          ...previous,
          loading: false,
          error: readErrorMessage(error, "知识成果加载失败"),
        }));
      });

    return () => {
      alive = false;
    };
  }, [context.archiveId]);

  useEffect(() => {
    if (!state.selectedObjectId) {
      return;
    }

    let alive = true;
    setState((previous) => ({ ...previous, detailLoading: true }));
    knowledgeResultsApi
      .getArchiveItemDetail(state.selectedObjectId, context.archiveId)
      .then((response) => {
        if (!alive) {
          return;
        }
        setState((previous) => ({
          ...previous,
          selectedDetail: response.data,
          detailLoading: false,
        }));
      })
      .catch(() => {
        if (!alive) {
          return;
        }
        setState((previous) => ({
          ...previous,
          selectedDetail: null,
          detailLoading: false,
        }));
      });

    return () => {
      alive = false;
    };
  }, [context.archiveId, state.selectedObjectId]);

  const selectedRow = useMemo(
    () => state.rows.find((item) => item.id === state.selectedObjectId) ?? null,
    [state.rows, state.selectedObjectId],
  );
  const rowById = useMemo(() => new Map(state.rows.map((row) => [row.id, row])), [state.rows]);
  const relationRows = useMemo<KnowledgeRelationRow[]>(
    () => state.graph?.edges.map((edge, index) => ({ ...edge, id: buildRelationId(edge, index) })) ?? [],
    [state.graph],
  );
  const selectedRelation = useMemo(
    () => relationRows.find((item) => item.id === state.selectedRelationId) ?? null,
    [relationRows, state.selectedRelationId],
  );
  const selectedEvidenceCoverage = {
    evidenceCount: state.selectedDetail?.evidence.length ?? 0,
    documentCount: state.selectedDetail?.documents.length ?? selectedRow?.documentCount ?? 0,
  };
  const publication = state.publication;
  const sourceMode = publication?.current_version
    ? {
        label: "正式入库知识",
        color: "green",
        description: `当前展示治理确认后的正式版本 ${publication.current_version.version_label}。`,
      }
    : context.publicationSnapshotId
      ? {
          label: "发布候选知识",
          color: "gold",
          description: "当前知识已生成候选快照，但尚未完成治理确认正式入库。",
        }
      : {
          label: "抽取工作态知识",
          color: "blue",
          description: "当前展示抽取/构建后的工作态知识，后续还需要质量评估、发布候选和治理确认。",
        };

  const objectColumns: ColumnsType<KnowledgeResultRow> = [
    {
      title: "知识名称",
      dataIndex: "name",
      render: (value: string, row) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{value}</Typography.Text>
          <Typography.Text type="secondary">{row.id}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "类型",
      dataIndex: "kind",
      width: 110,
      render: (kind: KnowledgeResultKind) => <Tag color={kindMeta[kind].color}>{kindMeta[kind].label}</Tag>,
    },
    { title: "分类", dataIndex: "category", width: 150 },
    { title: "覆盖文档", dataIndex: "documentCount", width: 100, align: "right" },
    {
      title: "摘要",
      dataIndex: "summary",
      ellipsis: true,
      render: (value: string) => value || "暂无摘要",
    },
  ];

  const relationColumns: ColumnsType<KnowledgeRelationRow> = [
    {
      title: "源对象",
      dataIndex: "source",
      render: (value: string) => rowById.get(value)?.name ?? value,
    },
    { title: "关系", dataIndex: "label" },
    {
      title: "目标对象",
      dataIndex: "target",
      render: (value: string) => rowById.get(value)?.name ?? value,
    },
  ];

  return (
    <PageFrame
      eyebrow="知识成果模块"
      title="知识成果查看"
      description="面向终端使用者查看当前知识库已经抽取出的知识对象、关系图谱、证据摘录和入库状态；不执行策略配置和系统间接口供应。"
    >
      {state.error ? <Alert className="p1-clean-alert" type="error" showIcon message="知识成果加载失败" description={state.error} /> : null}

      <Alert
        className="p1-clean-alert"
        type={publication?.current_version ? "success" : "info"}
        showIcon
        message={sourceMode.label}
        description={sourceMode.description}
      />

      <Spin spinning={state.loading}>
        <Row gutter={[16, 16]}>
          <Col xs={12} md={6}>
            <Card className="p1-clean-card">
              <Statistic title="文档数" value={state.summary?.document_count ?? 0} />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card className="p1-clean-card">
              <Statistic title="知识对象" value={state.rows.length} />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card className="p1-clean-card">
              <Statistic title="关系边" value={state.graph?.edges.length ?? 0} />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card className="p1-clean-card">
              <Statistic title="正式版本" value={publication?.current_version?.version_label ?? "未入库"} />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col xs={24} xl={15}>
            <Card className="p1-clean-card" title="知识对象与关系">
              <Tabs
                items={[
                  {
                    key: "graph",
                    label: "知识图谱",
                    children: (
                      <KnowledgeGraphPreview
                        graph={state.graph}
                        rows={state.rows}
                        selectedObjectId={state.selectedObjectId}
                        selectedRelationId={state.selectedRelationId}
                        visibleGraphMode={state.visibleGraphMode}
                        onSelect={(id) =>
                          setState((previous) => ({
                            ...previous,
                            selectedObjectId: id,
                            selectedRelationId: null,
                            visibleGraphMode: "focus_neighborhood",
                          }))
                        }
                        onSelectRelation={(relationId, sourceId) =>
                          setState((previous) => ({
                            ...previous,
                            selectedObjectId: sourceId,
                            selectedRelationId: relationId,
                            visibleGraphMode: "focus_neighborhood",
                          }))
                        }
                      />
                    ),
                  },
                  {
                    key: "objects",
                    label: "知识对象",
                    children: state.rows.length ? (
                      <Table
                        rowKey="id"
                        columns={objectColumns}
                        dataSource={state.rows}
                        pagination={{ pageSize: 8 }}
                        rowClassName={(row) => (row.id === state.selectedObjectId ? "p1-clean-table-row-selected" : "")}
                        onRow={(row) => ({
                          onClick: () =>
                            setState((previous) => ({
                              ...previous,
                              selectedObjectId: row.id,
                              selectedRelationId: null,
                              visibleGraphMode: "focus_neighborhood",
                            })),
                        })}
                      />
                    ) : (
                      <Empty description="暂无可查看的知识对象，请先完成资料接入和抽取运行。" />
                    ),
                  },
                  {
                    key: "relations",
                    label: "关系边",
                    children: relationRows.length ? (
                      <Table
                        rowKey="id"
                        columns={relationColumns}
                        dataSource={relationRows}
                        pagination={{ pageSize: 10 }}
                        rowClassName={(row) => (row.id === state.selectedRelationId ? "p1-clean-table-row-selected" : "")}
                        onRow={(row) => ({
                          onClick: () =>
                            setState((previous) => ({
                              ...previous,
                              selectedObjectId: row.source,
                              selectedRelationId: row.id,
                              visibleGraphMode: "focus_neighborhood",
                            })),
                        })}
                      />
                    ) : (
                      <Empty description="暂无关系边，后续需要补齐跨文档验证、合并与关系质量策略。" />
                    ),
                  },
                ]}
              />
            </Card>
          </Col>
          <Col xs={24} xl={9}>
            <Card className="p1-clean-card" title="知识详情与证据">
              <Spin spinning={state.detailLoading}>
                {selectedRow ? (
                  <Space direction="vertical" size={14} className="p1-results-detail">
                    <Descriptions column={1} size="small">
                      <Descriptions.Item label="名称">{state.selectedDetail?.name ?? selectedRow.name}</Descriptions.Item>
                      <Descriptions.Item label="类型">
                        <Tag color={kindMeta[selectedRow.kind].color}>{kindMeta[selectedRow.kind].label}</Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="分类">{state.selectedDetail?.category ?? selectedRow.category}</Descriptions.Item>
                      <Descriptions.Item label="覆盖文档">{state.selectedDetail?.document_count ?? selectedRow.documentCount}</Descriptions.Item>
                      <Descriptions.Item label="证据覆盖">
                        {selectedEvidenceCoverage.evidenceCount} 条摘录 / {selectedEvidenceCoverage.documentCount} 个来源
                      </Descriptions.Item>
                      <Descriptions.Item label="别名">
                        {(state.selectedDetail?.aliases.length ? state.selectedDetail.aliases : selectedRow.aliases).join(" / ") || "无"}
                      </Descriptions.Item>
                      {selectedRelation ? (
                        <Descriptions.Item label="选中关系">
                          {`${rowById.get(selectedRelation.source)?.name ?? selectedRelation.source} --${selectedRelation.label}--> ${
                            rowById.get(selectedRelation.target)?.name ?? selectedRelation.target
                          }`}
                        </Descriptions.Item>
                      ) : null}
                    </Descriptions>
                    <Typography.Paragraph>
                      {state.selectedDetail?.language_projection?.description_zh ||
                        state.selectedDetail?.interpretation.summary ||
                        selectedRow.summary ||
                        "暂无说明"}
                    </Typography.Paragraph>
                    {state.selectedDetail?.language_projection?.evidence_summary_zh ? (
                      <Alert
                        type="info"
                        showIcon
                        message="证据摘要"
                        description={state.selectedDetail.language_projection.evidence_summary_zh}
                      />
                    ) : null}
                    <List
                      size="small"
                      header="来源文档"
                      dataSource={state.selectedDetail?.documents ?? []}
                      locale={{ emptyText: "该对象暂无来源文档" }}
                      renderItem={(item) => (
                        <List.Item>
                          <Space direction="vertical" size={2}>
                            <Typography.Text>{item.title}</Typography.Text>
                            <Typography.Text type="secondary">{`${item.file_type} / ${item.source_archive} / ${item.id}`}</Typography.Text>
                          </Space>
                        </List.Item>
                      )}
                    />
                    <List
                      size="small"
                      header="证据摘录"
                      dataSource={state.selectedDetail?.evidence ?? []}
                      locale={{ emptyText: "该对象暂无可追溯证据摘录" }}
                      renderItem={(item) => (
                        <List.Item>
                          <Space direction="vertical" size={2}>
                            <Typography.Text>{item.excerpt}</Typography.Text>
                            <Typography.Text type="secondary">{item.document_title ?? item.document_id ?? "未知来源"}</Typography.Text>
                          </Space>
                        </List.Item>
                      )}
                    />
                    <List
                      size="small"
                      header="相关对象"
                      dataSource={state.selectedDetail?.related_items ?? []}
                      locale={{ emptyText: "暂无相关对象" }}
                      renderItem={(item) => (
                        <List.Item>
                          <Typography.Text>{`${item.name} / ${item.relation_type}`}</Typography.Text>
                        </List.Item>
                      )}
                    />
                  </Space>
                ) : (
                  <Empty description="请选择一个知识对象查看证据与关系。" />
                )}
              </Spin>
            </Card>
          </Col>
        </Row>
      </Spin>
    </PageFrame>
  );
}
