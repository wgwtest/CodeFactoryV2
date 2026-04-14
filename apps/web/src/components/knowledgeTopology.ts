import type { ArchiveKnowledgeGraph } from "../lib/api";

type VisibleGraph = {
  nodes: ArchiveKnowledgeGraph["nodes"];
  edges: ArchiveKnowledgeGraph["edges"];
  hiddenIsolatedCount: number;
  queryMode: boolean;
};

type CytoscapeLayout =
  | {
      name: "cose";
      fit: boolean;
      padding: number;
      animate: boolean;
      randomize: boolean;
      nodeRepulsion: number;
      idealEdgeLength: number;
    }
  | {
      name: "concentric";
      fit: boolean;
      padding: number;
      animate: boolean;
      minNodeSpacing: number;
      avoidOverlap: boolean;
      concentric: (node: { data: (key: string) => unknown }) => number;
      levelWidth: () => number;
    };

export function buildVisibleGraph(
  graph: ArchiveKnowledgeGraph,
  aliasesById: Map<string, string[]>,
  selectedItemTypes: string[],
  query = "",
): VisibleGraph {
  const normalizedQuery = query.trim().toLowerCase();

  if (selectedItemTypes.length === 0) {
    return {
      nodes: [],
      edges: [],
      hiddenIsolatedCount: 0,
      queryMode: Boolean(normalizedQuery),
    };
  }

  const selectedTypeSet = new Set(selectedItemTypes);
  const candidateNodes = graph.nodes.filter((node) => selectedTypeSet.has(node.item_type));
  const candidateNodeIds = new Set(candidateNodes.map((node) => node.id));
  const candidateEdges = graph.edges.filter(
    (edge) => candidateNodeIds.has(edge.source) && candidateNodeIds.has(edge.target),
  );
  const degreeById = buildDegreeIndex({ nodes: candidateNodes, edges: candidateEdges });

  if (!normalizedQuery) {
    const nodes = candidateNodes.filter((node) => (degreeById.get(node.id) ?? 0) > 0);
    const visibleNodeIds = new Set(nodes.map((node) => node.id));

    return {
      nodes,
      edges: candidateEdges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)),
      hiddenIsolatedCount: candidateNodes.length - nodes.length,
      queryMode: false,
    };
  }

  const matchedNodeIds = new Set(
    candidateNodes
      .filter((node) => {
        const haystack = [node.label, ...(aliasesById.get(node.id) ?? [])].join(" ").toLowerCase();
        return haystack.includes(normalizedQuery);
      })
      .map((node) => node.id),
  );

  if (matchedNodeIds.size === 0) {
    return {
      nodes: [],
      edges: [],
      hiddenIsolatedCount: 0,
      queryMode: true,
    };
  }

  const visibleNodeIds = new Set<string>(matchedNodeIds);
  candidateEdges.forEach((edge) => {
    if (matchedNodeIds.has(edge.source) || matchedNodeIds.has(edge.target)) {
      visibleNodeIds.add(edge.source);
      visibleNodeIds.add(edge.target);
    }
  });

  return {
    nodes: candidateNodes.filter((node) => visibleNodeIds.has(node.id)),
    edges: candidateEdges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)),
    hiddenIsolatedCount: 0,
    queryMode: true,
  };
}

export function getTopologyLayout(
  visibleGraph: VisibleGraph,
): CytoscapeLayout {
  if (visibleGraph.queryMode || visibleGraph.nodes.length <= 120) {
    return {
      name: "cose",
      fit: true,
      padding: 32,
      animate: false,
      randomize: true,
      nodeRepulsion: 180000,
      idealEdgeLength: 120,
    };
  }

  const degreeById = buildDegreeIndex({
    nodes: visibleGraph.nodes,
    edges: visibleGraph.edges,
  });

  return {
    name: "concentric",
    fit: true,
    padding: 40,
    animate: false,
    minNodeSpacing: 10,
    avoidOverlap: true,
    concentric: (node) => Number(degreeById.get(String(node.data("id"))) ?? 0),
    levelWidth: () => 1,
  };
}

function buildDegreeIndex(graph: Pick<ArchiveKnowledgeGraph, "nodes" | "edges">) {
  const degreeById = new Map(graph.nodes.map((node) => [node.id, 0]));

  graph.edges.forEach((edge) => {
    degreeById.set(edge.source, (degreeById.get(edge.source) ?? 0) + 1);
    degreeById.set(edge.target, (degreeById.get(edge.target) ?? 0) + 1);
  });

  return degreeById;
}
