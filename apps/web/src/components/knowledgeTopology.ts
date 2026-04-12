import type { ArchiveKnowledgeEntity, ArchiveKnowledgeGraph } from "../lib/api";

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
  entities: ArchiveKnowledgeEntity[],
  query: string,
): VisibleGraph {
  const normalizedQuery = query.trim().toLowerCase();
  const degreeById = buildDegreeIndex(graph);

  if (!normalizedQuery) {
    const nodes = graph.nodes.filter((node) => (degreeById.get(node.id) ?? 0) > 0);
    const visibleNodeIds = new Set(nodes.map((node) => node.id));

    return {
      nodes,
      edges: graph.edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)),
      hiddenIsolatedCount: graph.nodes.length - nodes.length,
      queryMode: false,
    };
  }

  const aliasesById = new Map(entities.map((entity) => [entity.id, entity.aliases]));
  const matchedNodeIds = new Set(
    graph.nodes
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
  graph.edges.forEach((edge) => {
    if (matchedNodeIds.has(edge.source) || matchedNodeIds.has(edge.target)) {
      visibleNodeIds.add(edge.source);
      visibleNodeIds.add(edge.target);
    }
  });

  return {
    nodes: graph.nodes.filter((node) => visibleNodeIds.has(node.id)),
    edges: graph.edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)),
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
    archive_id: "layout",
    nodes: visibleGraph.nodes,
    edges: visibleGraph.edges,
    summary: {
      archive_id: "layout",
      document_count: 0,
      entity_count: 0,
      event_count: 0,
      process_count: 0,
    },
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
