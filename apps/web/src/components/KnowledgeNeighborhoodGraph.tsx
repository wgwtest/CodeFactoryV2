import { Empty, Space, Tag, Typography } from "antd";
import ReactFlow, { Background, Controls, MarkerType, type Edge, type Node } from "react-flow-renderer";

import type { ArchiveKnowledgeItemGraph } from "../lib/api";

type KnowledgeNeighborhoodGraphProps = {
  graph: ArchiveKnowledgeItemGraph | null;
};

const categoryPalette: Record<string, string> = {
  architecture_artifact: "#e8f1ff",
  system_or_service: "#e6fffb",
  domain_process: "#fff7e6",
  operational_node: "#fff1f0",
  information_exchange: "#f9f0ff",
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

export function KnowledgeNeighborhoodGraph({ graph }: KnowledgeNeighborhoodGraphProps) {
  if (!graph || graph.nodes.length === 0) {
    return <Empty description="暂无关系邻域" />;
  }

  const flow = buildFlow(graph);

  return (
    <div>
      <Typography.Title level={5}>关系邻域</Typography.Title>
      <Typography.Paragraph type="secondary">
        中心节点为当前查看对象，周边节点展示已发布知识中的直接关联关系。
      </Typography.Paragraph>
      <div style={{ height: 340, border: "1px solid #f0f0f0", borderRadius: 12, overflow: "hidden" }}>
        <ReactFlow
          edges={flow.edges}
          fitView
          nodes={flow.nodes}
          nodesConnectable={false}
          nodesDraggable={false}
          elementsSelectable={false}
          zoomOnPinch={false}
        >
          <Background />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <Space wrap style={{ marginTop: 12 }}>
        {graph.nodes
          .filter((node) => !node.is_focus)
          .map((node) => (
            <Tag key={node.id}>{node.label}</Tag>
          ))}
      </Space>
    </div>
  );
}

function buildFlow(graph: ArchiveKnowledgeItemGraph): { nodes: Node[]; edges: Edge[] } {
  const focusNode = graph.nodes.find((node) => node.is_focus) ?? graph.nodes[0];
  const neighborNodes = graph.nodes.filter((node) => node.id !== focusNode.id);
  const radiusX = 210;
  const radiusY = 120;

  const nodes: Node[] = [
    {
      id: focusNode.id,
      data: { label: focusNode.label },
      position: { x: 260, y: 120 },
      style: {
        background: "#1677ff",
        color: "#ffffff",
        border: "1px solid #0958d9",
        borderRadius: 14,
        padding: 8,
        width: 164,
      },
    },
  ];

  neighborNodes.forEach((node, index) => {
    const angle = (2 * Math.PI * index) / Math.max(neighborNodes.length, 1);
    nodes.push({
      id: node.id,
      data: { label: node.label },
      position: {
        x: 260 + Math.cos(angle) * radiusX,
        y: 120 + Math.sin(angle) * radiusY,
      },
      style: {
        background: categoryPalette[node.category] ?? "#fafafa",
        border: "1px solid #d9d9d9",
        borderRadius: 14,
        padding: 8,
        width: 164,
      },
    });
  });

  const edges: Edge[] = graph.edges.map((edge, index) => ({
    id: `${edge.source}-${edge.target}-${index}`,
    source: edge.source,
    target: edge.target,
    label: relationLabels[edge.label] ?? edge.label,
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
  }));

  return { nodes, edges };
}
