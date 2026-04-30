import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, WheelEvent as ReactWheelEvent } from "react";
import { useNavigate } from "react-router-dom";

import {
  type P6MockScenarioCatalog,
  type P6PlatformDisplayBaselinePackage,
  type P6PlatformLegend,
  type P6PlatformRoutes,
  type P6PortalProjection,
  type P6SourceMode,
} from "../../lib/p6";
import { P6BlueprintArtifact } from "./P6BlueprintArtifact";
import { P6BlueprintLegend } from "./P6BlueprintLegend";
import { P6BlueprintNode } from "./P6BlueprintNode";
import { buildP6CssVariables } from "./p6Baseline";
import {
  P6_PORTAL_LAYOUT_STORAGE_KEY,
  P6_PORTAL_WORLD,
  type P6PortalAnchorSide,
  type P6PortalFlowEndpointId,
  type P6PortalNodeId,
  type P6PortalPosition,
  type P6PortalViewNode,
  defaultP6PortalLayout,
} from "./p6PortalData";
import {
  P6_PORTAL_NODE_PADDING,
  clampCameraToWorld,
  clampNodePosition,
  createP6PortalFitCamera,
  getPortalNodeById,
  type P6PortalCameraState as CameraState,
} from "./p6PortalGeometry";
import {
  buildPortalNodeRelationSnapshots,
  buildPortalProjectionSummary,
  buildPortalViewModel,
  getArtifactsForRelationshipView,
  hasStoredP6PortalLayout,
  readPersonalPortalLayout,
  type P6PortalLayoutMode,
  type P6PortalRelationshipViewMode,
} from "./p6PortalProjection";

type NodeDragState = {
  kind: "node";
  nodeId: P6PortalNodeId;
  startClientX: number;
  startClientY: number;
  origin: P6PortalPosition;
};

type PanDragState = {
  kind: "pan";
  startClientX: number;
  startClientY: number;
  origin: CameraState;
};

type DragState = NodeDragState | PanDragState;

type P6BlueprintCanvasProps = {
  archiveName: string;
  projection: P6PortalProjection;
  sourceMode: P6SourceMode;
  scenarioCatalog: P6MockScenarioCatalog;
  baseline: P6PlatformDisplayBaselinePackage;
  routes: P6PlatformRoutes;
  legend: P6PlatformLegend;
  selectedScenarioId: string;
  loading: boolean;
  error: string | null;
  onScenarioChange: (scenarioId: string) => void;
  onRetry: () => void;
};

const defaultCamera: CameraState = {
  x: 0,
  y: 0,
  scale: 1,
};

const deliveryCatalogEndpoint = {
  x: 1655,
  y: 730,
  width: 0,
  height: 0,
};

const MAX_VISIBLE_FLOW_PAYLOADS = 24;

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function getAnchorPoint(
  node: ReturnType<typeof getPortalNodeById>,
  position: P6PortalPosition,
  side: P6PortalAnchorSide,
) {
  switch (side) {
    case "left":
      return { x: position.x, y: position.y + node.height / 2 };
    case "right":
      return { x: position.x + node.width, y: position.y + node.height / 2 };
    case "top":
      return { x: position.x + node.width / 2, y: position.y };
    case "bottom":
      return { x: position.x + node.width / 2, y: position.y + node.height };
    default:
      return { x: position.x, y: position.y };
  }
}

function isPortalNodeId(endpointId: P6PortalFlowEndpointId): endpointId is P6PortalNodeId {
  return endpointId === "p1" || endpointId === "p2" || endpointId === "p3" || endpointId === "p4" || endpointId === "p5";
}

function getFlowEndpointPoint(
  endpointId: P6PortalFlowEndpointId,
  side: P6PortalAnchorSide,
  layout: Record<P6PortalNodeId, P6PortalPosition>,
  nodes: ReturnType<typeof buildPortalViewModel>["nodes"],
) {
  if (endpointId === "delivery-catalog") {
    return { x: deliveryCatalogEndpoint.x, y: deliveryCatalogEndpoint.y };
  }

  return getAnchorPoint(getPortalNodeById(nodes, endpointId), layout[endpointId], side);
}

function getControlPoint(point: { x: number; y: number }, side: P6PortalAnchorSide, distance: number) {
  switch (side) {
    case "left":
      return { x: point.x - distance, y: point.y };
    case "right":
      return { x: point.x + distance, y: point.y };
    case "top":
      return { x: point.x, y: point.y - distance };
    case "bottom":
      return { x: point.x, y: point.y + distance };
    default:
      return point;
  }
}

function createFlowPath(
  flow: ReturnType<typeof buildPortalViewModel>["flows"][number],
  layout: Record<P6PortalNodeId, P6PortalPosition>,
  nodeIds: ReturnType<typeof buildPortalViewModel>["nodes"],
) {
  const fromPoint = getFlowEndpointPoint(flow.from, flow.fromSide, layout, nodeIds);
  const toPoint = getFlowEndpointPoint(flow.to, flow.toSide, layout, nodeIds);
  const distance = Math.max(Math.abs(toPoint.x - fromPoint.x) * 0.38, Math.abs(toPoint.y - fromPoint.y) * 0.32, 120);
  const controlA = getControlPoint(fromPoint, flow.fromSide, distance);
  const controlB = getControlPoint(toPoint, flow.toSide, distance);

  return {
    d: `M ${fromPoint.x} ${fromPoint.y} C ${controlA.x} ${controlA.y}, ${controlB.x} ${controlB.y}, ${toPoint.x} ${toPoint.y}`,
    labelPosition: {
      x: (fromPoint.x + toPoint.x) / 2,
      y: (fromPoint.y + toPoint.y) / 2,
    },
  };
}

function getVisiblePins(flows: ReturnType<typeof buildPortalViewModel>["flows"], nodeId: P6PortalNodeId) {
  const sides = new Set<P6PortalAnchorSide>();

  flows.forEach((flow) => {
    if (flow.from === nodeId) {
      sides.add(flow.fromSide);
    }
    if (flow.to === nodeId) {
      sides.add(flow.toSide);
    }
  });

  return Array.from(sides);
}

function getFlowFallbackPayloadLabel(label: string) {
  if (label.includes("知识")) {
    return "知识";
  }
  if (label.includes("规格") || label.includes("需求")) {
    return "规格";
  }
  if (label.includes("工单")) {
    return "工单";
  }
  if (label.includes("基线")) {
    return "基线";
  }
  if (label.includes("工具")) {
    return "工具";
  }
  if (label.includes("目录") || label.includes("交付")) {
    return "目录";
  }
  return label.slice(0, 2);
}

function isModuleNode(node: P6PortalViewNode): node is Extract<P6PortalViewNode, { kind: "module" }> {
  return node.kind === "module";
}

function getFlowPayloadLabel(flow: ReturnType<typeof buildPortalViewModel>["flows"][number]) {
  switch (flow.semanticLabel) {
    case "knowledge_supply":
      return "知识";
    case "requirement_to_design":
      return "规格";
    case "work_order_package":
      return "工单";
    case "design_baseline_to_build":
      return "基线";
    case "tool_supply":
      return "工具";
    case "delivery_catalog_output":
      return "目录";
    default:
      return getFlowFallbackPayloadLabel(flow.label);
  }
}

function normalizeFlowTargetLabel(label: string) {
  return label.trim().toLowerCase();
}

function getFlowTargetLabels(
  endpointId: P6PortalFlowEndpointId,
  nodes: ReturnType<typeof buildPortalViewModel>["nodes"],
) {
  if (endpointId === "delivery-catalog") {
    return ["交付目录", "delivery-catalog"];
  }

  const targetNode = getPortalNodeById(nodes, endpointId);
  if (!isModuleNode(targetNode)) {
    return [endpointId];
  }

  return [targetNode.stage, targetNode.title, endpointId];
}

function parseFlowCount(value: string | number | undefined | null) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.max(0, Math.round(value));
  }

  if (!value) {
    return null;
  }

  const matched = String(value).match(/\d+(?:\.\d+)?/);
  if (!matched) {
    return null;
  }

  return Math.max(0, Math.round(Number(matched[0])));
}

function getFlowPayloadConfig(
  flow: ReturnType<typeof buildPortalViewModel>["flows"][number],
  nodes: ReturnType<typeof buildPortalViewModel>["nodes"],
) {
  const payloadLabel = getFlowPayloadLabel(flow);
  const sourceNode = isPortalNodeId(flow.from) ? getPortalNodeById(nodes, flow.from) : null;
  const targetLabels = getFlowTargetLabels(flow.to, nodes).map(normalizeFlowTargetLabel);
  const matchingOutputPort =
    sourceNode && isModuleNode(sourceNode)
      ? (sourceNode.stageCard.flow_port_items ?? []).find((port) => {
          const portTarget = normalizeFlowTargetLabel(port.connected_target);
          return port.direction === "output" && targetLabels.includes(portTarget);
        })
      : undefined;
  const matchingOutputCounter =
    sourceNode && isModuleNode(sourceNode)
      ? (sourceNode.stageCard.live_counter_items ?? []).find((counter) => {
          return counter.direction === "output" && (counter.label.includes(payloadLabel) || counter.key.includes(flow.semanticLabel));
        })
      : undefined;
  const sourceCount =
    parseFlowCount(matchingOutputPort?.current_rate) ??
    parseFlowCount(matchingOutputCounter?.value) ??
    parseFlowCount(matchingOutputCounter?.unit) ??
    1;
  const tokenCount = clamp(sourceCount, sourceCount === 0 ? 0 : 1, MAX_VISIBLE_FLOW_PAYLOADS);

  return {
    label: payloadLabel,
    sourceCount,
    tokenCount,
    rate: matchingOutputPort?.current_rate ?? `${sourceCount}`,
    truncated: sourceCount > MAX_VISIBLE_FLOW_PAYLOADS,
  };
}

function getFlowPayloadDuration(tokenCount: number) {
  return clamp(5.4 + tokenCount * 0.16, 6, 10);
}

export function P6BlueprintCanvas({
  archiveName,
  projection,
  sourceMode,
  scenarioCatalog,
  baseline,
  routes,
  legend,
  selectedScenarioId,
  loading,
  error,
  onScenarioChange,
  onRetry,
}: P6BlueprintCanvasProps) {
  const navigate = useNavigate();
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const personalLayoutRef = useRef<Record<P6PortalNodeId, P6PortalPosition>>(readPersonalPortalLayout());
  const [layout, setLayout] = useState<Record<P6PortalNodeId, P6PortalPosition>>(() => readPersonalPortalLayout());
  const [camera, setCamera] = useState<CameraState>(defaultCamera);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<P6PortalNodeId | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<P6PortalNodeId | null>(null);
  const [activeFlowIndex, setActiveFlowIndex] = useState(0);
  const [layoutMode, setLayoutMode] = useState<P6PortalLayoutMode>(() => (hasStoredP6PortalLayout() ? "personal" : "system"));
  const [relationshipMode, setRelationshipMode] = useState<P6PortalRelationshipViewMode>("semantic");
  const { nodes, flows, artifacts } = useMemo(() => buildPortalViewModel(projection), [projection]);
  const selectedScenario = scenarioCatalog.items.find((item) => item.scenario_id === selectedScenarioId) ?? scenarioCatalog.items[0];
  const p5Node = nodes.find((node): node is Extract<P6PortalViewNode, { kind: "module" }> => node.id === "p5" && isModuleNode(node));
  const deliveryVersionMetric = (p5Node?.stageCard.system_overall_metric_items ?? []).find(
    (metric) => metric.key.includes("delivery") || metric.label.includes("版本"),
  );

  const focusNodeId = hoveredNodeId ?? selectedNodeId;
  const activeFlow = flows[activeFlowIndex] ?? flows[0];
  const relationSnapshots = useMemo(() => buildPortalNodeRelationSnapshots(nodes, flows, artifacts), [nodes, flows, artifacts]);
  const projectionSummary = useMemo(
    () => buildPortalProjectionSummary(archiveName, layoutMode, relationshipMode, projection),
    [archiveName, layoutMode, relationshipMode, projection],
  );
  const visibleArtifacts = useMemo(
    () => getArtifactsForRelationshipView(relationshipMode, focusNodeId, artifacts),
    [artifacts, focusNodeId, relationshipMode],
  );

  useEffect(() => {
    if (selectedNodeId && !nodes.some((node) => node.id === selectedNodeId)) {
      setSelectedNodeId(null);
    }
  }, [nodes, selectedNodeId]);

  useEffect(() => {
    function fitViewport() {
      const viewportRect = viewportRef.current?.getBoundingClientRect();
      setCamera(
        createP6PortalFitCamera({
          width: viewportRect?.width,
          height: viewportRect?.height,
        }),
      );
    }

    fitViewport();
    window.addEventListener("resize", fitViewport);

    return () => window.removeEventListener("resize", fitViewport);
  }, []);

  useEffect(() => {
    if (layoutMode !== "personal") {
      return;
    }

    personalLayoutRef.current = layout;
    window.localStorage.setItem(P6_PORTAL_LAYOUT_STORAGE_KEY, JSON.stringify(layout));
  }, [layout, layoutMode]);

  useEffect(() => {
    if (flows.length === 0) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setActiveFlowIndex((current) => (current + 1) % flows.length);
    }, 2200);

    return () => window.clearInterval(timer);
  }, [flows.length]);

  useEffect(() => {
    if (!dragState) {
      return undefined;
    }

    const currentDrag = dragState;

    function handleMouseMove(event: MouseEvent) {
      if (currentDrag.kind === "pan") {
        const viewportRect = viewportRef.current?.getBoundingClientRect();
        const nextCamera = {
          x: currentDrag.origin.x + event.clientX - currentDrag.startClientX,
          y: currentDrag.origin.y + event.clientY - currentDrag.startClientY,
          scale: currentDrag.origin.scale,
        };

        setCamera(
          clampCameraToWorld(nextCamera, {
            width: viewportRect?.width,
            height: viewportRect?.height,
          }),
        );
        return;
      }

      const nextX = currentDrag.origin.x + (event.clientX - currentDrag.startClientX) / camera.scale;
      const nextY = currentDrag.origin.y + (event.clientY - currentDrag.startClientY) / camera.scale;

      setLayout((current) => ({
        ...current,
        [currentDrag.nodeId]: clampNodePosition(nodes, currentDrag.nodeId, {
          x: nextX,
          y: nextY,
        }),
      }));
      setLayoutMode("personal");
    }

    function handleMouseUp() {
      setDragState(null);
    }

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [camera.scale, dragState, nodes]);

  const flowPaths = useMemo(
    () =>
      flows.map((flow) => ({
        ...flow,
        ...createFlowPath(flow, layout, nodes),
      })),
    [flows, layout, nodes],
  );

  const emphasizedArtifactIds = new Set<(typeof artifacts)[number]["id"]>();

  const emphasizedFlowIds = new Set<string>();
  const emphasizedNodeIds = new Set<P6PortalNodeId>();

  if (focusNodeId) {
    emphasizedNodeIds.add(focusNodeId);
    flows.forEach((flow) => {
      if (flow.from === focusNodeId || flow.to === focusNodeId) {
        emphasizedFlowIds.add(flow.id);
        if (isPortalNodeId(flow.from)) {
          emphasizedNodeIds.add(flow.from);
        }
        if (isPortalNodeId(flow.to)) {
          emphasizedNodeIds.add(flow.to);
        }
      }
    });
    artifacts.forEach((artifact) => {
      if (artifact.linkedNodeIds.includes(focusNodeId)) {
        emphasizedArtifactIds.add(artifact.id);
      }
    });
  } else if (activeFlow) {
    emphasizedFlowIds.add(activeFlow.id);
    if (isPortalNodeId(activeFlow.from)) {
      emphasizedNodeIds.add(activeFlow.from);
    }
    if (isPortalNodeId(activeFlow.to)) {
      emphasizedNodeIds.add(activeFlow.to);
    }
  }

  function handleViewportWheel(event: ReactWheelEvent<HTMLDivElement>) {
    event.preventDefault();
    const viewportRect = viewportRef.current?.getBoundingClientRect();
    if (!viewportRect) {
      return;
    }

    const pointerX = event.clientX - viewportRect.left;
    const pointerY = event.clientY - viewportRect.top;
    const worldX = (pointerX - camera.x) / camera.scale;
    const worldY = (pointerY - camera.y) / camera.scale;
    const nextScale = clamp(camera.scale * (event.deltaY > 0 ? 0.92 : 1.08), 0.54, 1.24);

    setCamera(
      clampCameraToWorld(
        {
          x: pointerX - worldX * nextScale,
          y: pointerY - worldY * nextScale,
          scale: nextScale,
        },
        {
          width: viewportRect.width,
          height: viewportRect.height,
        },
      ),
    );
  }

  return (
    <div id="p6-portal-page" className="p6-portal-page" style={buildP6CssVariables(baseline)}>
      <header className="p6-portal-hud-title" aria-label="门户状态">
        <p>CodeFactoryV2 / P6.1</p>
        <h1>五阶段运行语义画布</h1>
        <span>推荐布局 · {sourceMode === "mock" ? "mock projection" : "live projection"} · {loading ? "刷新中" : "100%"}</span>
      </header>

      <div className="p6-portal-source-control" data-testid="p6-portal-source-control">
        <div className="p6-portal-source-control__topline">
          <span className="p6-portal-source-control__badge">{sourceMode === "mock" ? "模拟源" : "真实源"}</span>
          <span className="p6-portal-source-control__state">{loading ? "刷新中" : "已装载"}</span>
        </div>
        <div className="p6-portal-source-control__buttons">
          {scenarioCatalog.items.map((item) => (
            <button
              key={item.scenario_id}
              type="button"
              className={[
                "p6-portal-source-control__button",
                item.scenario_id === selectedScenarioId ? "is-active" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => onScenarioChange(item.scenario_id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="p6-portal-source-control__hint">{selectedScenario?.description}</div>
        {error ? (
          <div className="p6-portal-source-control__error">
            <span>{error}</span>
            <button type="button" className="p6-portal-source-control__retry" onClick={onRetry}>
              重试
            </button>
          </div>
        ) : null}
      </div>

      <div
        id="p6-portal-viewport"
        ref={viewportRef}
        className="p6-portal-viewport"
        onWheel={handleViewportWheel}
        onMouseDown={(event) => {
          if (event.target !== event.currentTarget) {
            return;
          }

          setSelectedNodeId(null);
          setDragState({
            kind: "pan",
            startClientX: event.clientX,
            startClientY: event.clientY,
            origin: camera,
          });
        }}
      >
        <div className="p6-portal-viewport__background-grid" />

        <div
          id="p6-portal-stage"
          data-testid="p6-portal-stage"
          className="p6-portal-stage"
          style={{
            width: `${P6_PORTAL_WORLD.width}px`,
            height: `${P6_PORTAL_WORLD.height}px`,
            transform: `translate(${camera.x}px, ${camera.y}px) scale(${camera.scale})`,
          }}
        >
          <svg
            className="p6-portal-stage__wires"
            viewBox={`0 0 ${P6_PORTAL_WORLD.width} ${P6_PORTAL_WORLD.height}`}
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            {flowPaths.map((flow) => (
              <Fragment key={flow.id}>
                <g>
                  <path
                    d={flow.d}
                    className={[
                      "p6-portal-wire",
                      `p6-portal-wire--${flow.tone}`,
                      `p6-portal-wire--flow-${flow.id}`,
                      `p6-portal-wire--${flow.renderStyle}`,
                      emphasizedFlowIds.has(flow.id) ? "is-emphasized" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                  />
                </g>
              </Fragment>
            ))}
            {relationshipMode === "semantic"
              ? flowPaths.map((flow, flowIndex) => {
                  const payload = getFlowPayloadConfig(flow, nodes);
                  const duration = getFlowPayloadDuration(payload.tokenCount);
                  const interval = payload.tokenCount > 0 ? duration / payload.tokenCount : duration;
                  const tokenWidth = payload.label.length > 2 ? 52 : 46;

                  return (
                    <Fragment key={`${flow.id}-payloads`}>
                      <g className="p6-portal-flow-payloads">
                        {Array.from({ length: payload.tokenCount }, (_, tokenIndex) => (
                          <Fragment key={`${flow.id}-${tokenIndex}`}>
                            <g
                              data-testid={`p6-flow-payload-${flow.id}-${tokenIndex}`}
                              data-flow-id={flow.id}
                              data-payload-label={payload.label}
                              data-payload-rate={payload.rate}
                              data-payload-source-count={`${payload.sourceCount}`}
                              data-payload-token-count={`${payload.tokenCount}`}
                              data-payload-truncated={payload.truncated ? "true" : "false"}
                              className={[
                                "p6-portal-flow-payload",
                                `p6-portal-flow-payload--${flow.tone}`,
                                `p6-portal-flow-payload--flow-${flow.id}`,
                                emphasizedFlowIds.has(flow.id) ? "is-emphasized" : "",
                              ]
                                .filter(Boolean)
                                .join(" ")}
                            >
                              <rect
                                className="p6-portal-flow-payload__shell"
                                x={-tokenWidth / 2}
                                y={-12}
                                width={tokenWidth}
                                height={24}
                                rx={12}
                              />
                              <circle className="p6-portal-flow-payload__dot" cx={-tokenWidth / 2 + 12} cy={0} r={3.6} />
                              <text className="p6-portal-flow-payload__text" x={4} y={4} textAnchor="middle">
                                {payload.label}
                              </text>
                              <animateMotion
                                path={flow.d}
                                dur={`${duration.toFixed(2)}s`}
                                begin={`-${(tokenIndex * interval + flowIndex * 0.19).toFixed(2)}s`}
                                repeatCount="indefinite"
                                calcMode="linear"
                              />
                            </g>
                          </Fragment>
                        ))}
                      </g>
                    </Fragment>
                  );
                })
              : null}
          </svg>

          <div
            data-testid="p6-terminal-output-delivery-catalog"
            className="p6-portal-terminal-output"
            style={{
              left: `${deliveryCatalogEndpoint.x}px`,
              top: `${deliveryCatalogEndpoint.y - 65}px`,
            }}
          >
            <span className="p6-portal-terminal-output__pin" />
            <strong>交付目录</strong>
            <span>版本包 / 部署说明 / 验证记录</span>
            <b>
              {deliveryVersionMetric
                ? `${deliveryVersionMetric.value}${deliveryVersionMetric.unit ?? ""}`
                : "86个"}{" "}
              版本
            </b>
          </div>

          {visibleArtifacts.map((artifact) => (
            <P6BlueprintArtifact key={artifact.id} artifact={artifact} emphasized={emphasizedArtifactIds.has(artifact.id)} />
          ))}

          {nodes.map((node) => (
            <P6BlueprintNode
              key={node.id}
              node={node}
              position={layout[node.id]}
              active={selectedNodeId === node.id}
              emphasized={emphasizedNodeIds.has(node.id)}
              visiblePins={getVisiblePins(flows, node.id)}
              relationSummary={relationshipMode === "projection" ? relationSnapshots[node.id]?.label : undefined}
              onClick={() => {
                setSelectedNodeId(node.id);
              }}
              onDoubleClick={() => {
                if (node.kind === "module") {
                  navigate(routes.stage_routes[node.stage]?.path ?? node.route ?? "/portal");
                }
              }}
              onMouseEnter={() => setHoveredNodeId(node.id)}
              onMouseLeave={() => setHoveredNodeId((current) => (current === node.id ? null : current))}
              onMouseDown={(event: ReactMouseEvent<HTMLButtonElement>) => {
                event.stopPropagation();
                if (event.button !== 0) {
                  return;
                }

                setSelectedNodeId(node.id);
                setDragState({
                  kind: "node",
                  nodeId: node.id,
                  startClientX: event.clientX,
                  startClientY: event.clientY,
                  origin: layout[node.id],
                });
              }}
            />
          ))}
        </div>
      </div>

      <P6BlueprintLegend
        archiveName={archiveName}
        legend={legend}
        projectionSummary={projectionSummary}
        layoutMode={layoutMode}
        relationshipMode={relationshipMode}
        hasPersonalLayout={hasStoredP6PortalLayout()}
        onLayoutModeChange={(mode) => {
          setLayoutMode(mode);
          setLayout(mode === "system" ? defaultP6PortalLayout : personalLayoutRef.current);
        }}
        onRelationshipModeChange={setRelationshipMode}
        onResetView={(event) => {
          event.stopPropagation();
          const viewportRect = viewportRef.current?.getBoundingClientRect();
          setCamera(
            createP6PortalFitCamera({
              width: viewportRect?.width,
              height: viewportRect?.height,
            }),
          );
          setLayout(layoutMode === "system" ? defaultP6PortalLayout : personalLayoutRef.current);
          setSelectedNodeId(null);
        }}
      />
    </div>
  );
}
