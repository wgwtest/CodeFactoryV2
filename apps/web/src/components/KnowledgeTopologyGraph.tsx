import { useEffect, useMemo, useRef } from "react";
import { Card, Empty, Space, Tag, Typography } from "antd";
import cytoscape from "cytoscape";

import type { ArchiveKnowledgeEntity, ArchiveKnowledgeGraph } from "../lib/api";
import { buildVisibleGraph, getTopologyLayout } from "./knowledgeTopology";

type KnowledgeTopologyGraphProps = {
  entities: ArchiveKnowledgeEntity[];
  graph: ArchiveKnowledgeGraph;
  query: string;
  selectedEntityId: string | null;
  onSelectEntity: (id: string) => void;
};

const categoryPalette: Record<string, { fill: string; border: string; label: string }> = {
  architecture_artifact: { fill: "#dbeafe", border: "#60a5fa", label: "架构产物" },
  architecture_concept: { fill: "#e0f2fe", border: "#38bdf8", label: "架构概念" },
  domain_concept: { fill: "#dcfce7", border: "#4ade80", label: "领域概念" },
  domain_process: { fill: "#fef3c7", border: "#f59e0b", label: "流程" },
  organization: { fill: "#fee2e2", border: "#f87171", label: "组织" },
  system_or_service: { fill: "#ccfbf1", border: "#2dd4bf", label: "系统/服务" },
  operational_node: { fill: "#fce7f3", border: "#f472b6", label: "运行节点" },
  information_exchange: { fill: "#ede9fe", border: "#8b5cf6", label: "信息交换" },
  timeline_event: { fill: "#ffedd5", border: "#fb923c", label: "时间事件" },
};

const relationLabels: Record<string, string> = {
  part_of: "组成/隶属",
  describes: "描述",
  owned_by: "责任归属",
  operational_exchange: "运行交换",
  participates_in_exchange: "参与交换",
  scoped_by: "阶段约束",
  process_scoped_by: "阶段约束",
};

export function KnowledgeTopologyGraph({
  entities,
  graph,
  query,
  selectedEntityId,
  onSelectEntity,
}: KnowledgeTopologyGraphProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const visibleGraph = useMemo(() => buildVisibleGraph(graph, entities, query), [entities, graph, query]);
  const supportsCanvas = canRenderCanvas();

  useEffect(() => {
    const container = containerRef.current;
    if (!container || visibleGraph.nodes.length === 0 || !supportsCanvas) {
      cyRef.current?.destroy();
      cyRef.current = null;
      return;
    }

    const showEdgeLabels = visibleGraph.nodes.length <= 40;
    const cy = cytoscape({
      container,
      elements: [
        ...visibleGraph.nodes.map((node) => {
          const palette = categoryPalette[node.type] ?? {
            fill: "#f8fafc",
            border: "#94a3b8",
            label: node.type,
          };

          return {
            data: {
              id: node.id,
              label: node.label,
              category: palette.label,
              fill: palette.fill,
              border: palette.border,
            },
          };
        }),
        ...visibleGraph.edges.map((edge, index) => ({
          data: {
            id: `${edge.source}-${edge.target}-${index}`,
            source: edge.source,
            target: edge.target,
            label: showEdgeLabels ? relationLabels[edge.label] ?? edge.label : "",
          },
        })),
      ],
      layout: getTopologyLayout(visibleGraph),
      minZoom: 0.2,
      maxZoom: 2.5,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(fill)",
            "border-color": "data(border)",
            "border-width": 1.5,
            color: "#0f172a",
            label: "data(label)",
            "font-size": 11,
            "font-weight": 600,
            "text-wrap": "wrap",
            "text-max-width": 88,
            "text-valign": "center",
            "text-halign": "center",
            width: 44,
            height: 44,
            padding: "10px",
          },
        },
        {
          selector: "node.is-selected",
          style: {
            "border-width": 3,
            "border-color": "#1677ff",
            "overlay-color": "#93c5fd",
            "overlay-opacity": 0.16,
            "overlay-padding": 6,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.2,
            "line-color": "rgba(100, 116, 139, 0.45)",
            "target-arrow-color": "rgba(100, 116, 139, 0.55)",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 9,
            color: "#475569",
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.9,
            "text-background-padding": 2,
          },
        },
      ],
    });

    cy.on("tap", "node", (event) => {
      onSelectEntity(event.target.id());
    });

    cyRef.current = cy;

    return () => {
      if (cyRef.current === cy) {
        cyRef.current = null;
      }
      cy.destroy();
    };
  }, [onSelectEntity, supportsCanvas, visibleGraph]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) {
      return;
    }

    cy.batch(() => {
      cy.nodes().removeClass("is-selected");
      if (selectedEntityId) {
        cy.$id(selectedEntityId).addClass("is-selected");
      }
    });
  }, [selectedEntityId]);

  if (visibleGraph.nodes.length === 0) {
    return (
      <Card
        variant="borderless"
        style={{ borderRadius: 20, boxShadow: "0 14px 32px rgba(15, 23, 42, 0.06)" }}
        styles={{ body: { padding: 24 } }}
      >
        <Typography.Title level={5} style={{ marginTop: 0 }}>
          全局拓扑图
        </Typography.Title>
        <Empty description="当前筛选条件下暂无可显示节点" />
      </Card>
    );
  }

  const categoryLegend = Array.from(
    new Map(
      visibleGraph.nodes.map((node) => {
        const palette = categoryPalette[node.type] ?? {
          fill: "#f8fafc",
          border: "#94a3b8",
          label: node.type,
        };
        return [node.type, palette];
      }),
    ).values(),
  );

  return (
    <Card
      variant="borderless"
      style={{ borderRadius: 20, boxShadow: "0 14px 32px rgba(15, 23, 42, 0.06)" }}
      styles={{ body: { padding: 24 } }}
    >
      <Space direction="vertical" size={14} style={{ display: "flex" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <div>
            <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 4 }}>
              全局拓扑图
            </Typography.Title>
            <Typography.Text type="secondary">
              点击节点可直接打开详情；输入搜索词后，图中仅保留命中节点及其一度关联。
            </Typography.Text>
          </div>
          <Space wrap size={[8, 8]}>
            <Tag color="blue" style={{ borderRadius: 999, paddingInline: 12, lineHeight: "28px", marginInlineEnd: 0 }}>
              {visibleGraph.queryMode ? `命中节点：${visibleGraph.nodes.length}` : `已展示关联节点：${visibleGraph.nodes.length}`}
            </Tag>
            <Tag style={{ borderRadius: 999, paddingInline: 12, lineHeight: "28px", marginInlineEnd: 0 }}>
              关系：{visibleGraph.edges.length}
            </Tag>
            {!visibleGraph.queryMode && visibleGraph.hiddenIsolatedCount > 0 ? (
              <Tag style={{ borderRadius: 999, paddingInline: 12, lineHeight: "28px", marginInlineEnd: 0 }}>
                已折叠孤立节点：{visibleGraph.hiddenIsolatedCount}
              </Tag>
            ) : null}
          </Space>
        </div>

        <div
          ref={containerRef}
          data-testid="knowledge-topology-graph"
          style={{
            height: 620,
            borderRadius: 16,
            border: "1px solid rgba(148, 163, 184, 0.18)",
            background:
              "radial-gradient(circle at top left, rgba(219,234,254,0.34), transparent 32%), linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)",
          }}
        >
          {!supportsCanvas ? (
            <div
              style={{
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#64748b",
                fontSize: 14,
              }}
            >
              当前环境未启用图谱画布，浏览器中将显示可交互拓扑。
            </div>
          ) : null}
        </div>

        <Space wrap size={[8, 8]}>
          {categoryLegend.map((item) => (
            <Tag
              key={item.label}
              style={{
                borderRadius: 999,
                paddingInline: 10,
                lineHeight: "24px",
                marginInlineEnd: 0,
                background: item.fill,
                borderColor: item.border,
              }}
            >
              {item.label}
            </Tag>
          ))}
        </Space>
      </Space>
    </Card>
  );
}

function canRenderCanvas() {
  if (typeof document === "undefined") {
    return false;
  }

  if (typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent)) {
    return false;
  }

  try {
    const canvas = document.createElement("canvas");
    return typeof canvas.getContext === "function" && canvas.getContext("2d") !== null;
  } catch {
    return false;
  }
}
