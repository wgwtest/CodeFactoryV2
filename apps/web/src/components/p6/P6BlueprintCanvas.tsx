import { useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, WheelEvent as ReactWheelEvent } from "react";
import { useNavigate } from "react-router-dom";

import { P6BlueprintArtifact } from "./P6BlueprintArtifact";
import { P6BlueprintLegend } from "./P6BlueprintLegend";
import { P6BlueprintNode } from "./P6BlueprintNode";
import {
  P6_PORTAL_LAYOUT_STORAGE_KEY,
  P6_PORTAL_WORLD,
  type P6PortalAnchorSide,
  p6PortalArtifacts,
  type P6PortalFlow,
  type P6PortalNode,
  type P6PortalNodeId,
  type P6PortalPosition,
  defaultP6PortalLayout,
  p6PortalFlows,
  p6PortalNodes,
} from "./p6PortalData";
import {
  P6_PORTAL_NODE_PADDING,
  clampCameraToWorld,
  clampNodePosition,
  getPortalNodeById,
  type P6PortalCameraState as CameraState,
} from "./p6PortalGeometry";
import {
  buildPortalNodeRelationSnapshots,
  buildPortalProjectionSummary,
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

const defaultCamera: CameraState = {
  x: 24,
  y: 36,
  scale: 0.72,
};

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function getAnchorPoint(node: P6PortalNode, position: P6PortalPosition, side: P6PortalAnchorSide) {
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

function createFlowPath(flow: P6PortalFlow, layout: Record<P6PortalNodeId, P6PortalPosition>) {
  const fromNode = getPortalNodeById(flow.from);
  const toNode = getPortalNodeById(flow.to);
  const fromPoint = getAnchorPoint(fromNode, layout[flow.from], flow.fromSide);
  const toPoint = getAnchorPoint(toNode, layout[flow.to], flow.toSide);
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

function getVisiblePins(nodeId: P6PortalNodeId) {
  const sides = new Set<P6PortalAnchorSide>();

  p6PortalFlows.forEach((flow) => {
    if (flow.from === nodeId) {
      sides.add(flow.fromSide);
    }
    if (flow.to === nodeId) {
      sides.add(flow.toSide);
    }
  });

  return Array.from(sides);
}

export function P6BlueprintCanvas({ archiveName }: { archiveName: string }) {
  const navigate = useNavigate();
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const personalLayoutRef = useRef<Record<P6PortalNodeId, P6PortalPosition>>(readPersonalPortalLayout());
  const [layout, setLayout] = useState<Record<P6PortalNodeId, P6PortalPosition>>(() => readPersonalPortalLayout());
  const [camera, setCamera] = useState<CameraState>(defaultCamera);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<P6PortalNodeId | null>("p2");
  const [hoveredNodeId, setHoveredNodeId] = useState<P6PortalNodeId | null>(null);
  const [activeFlowIndex, setActiveFlowIndex] = useState(0);
  const [layoutMode, setLayoutMode] = useState<P6PortalLayoutMode>(() => (hasStoredP6PortalLayout() ? "personal" : "system"));
  const [relationshipMode, setRelationshipMode] = useState<P6PortalRelationshipViewMode>("semantic");

  const focusNodeId = hoveredNodeId ?? selectedNodeId;
  const activeFlow = p6PortalFlows[activeFlowIndex] ?? p6PortalFlows[0];
  const relationSnapshots = useMemo(() => buildPortalNodeRelationSnapshots(), []);
  const projectionSummary = useMemo(
    () => buildPortalProjectionSummary(archiveName, layoutMode, relationshipMode),
    [archiveName, layoutMode, relationshipMode],
  );
  const visibleArtifacts = useMemo(
    () => getArtifactsForRelationshipView(relationshipMode, focusNodeId),
    [focusNodeId, relationshipMode],
  );

  useEffect(() => {
    if (layoutMode !== "personal") {
      return;
    }

    personalLayoutRef.current = layout;
    window.localStorage.setItem(P6_PORTAL_LAYOUT_STORAGE_KEY, JSON.stringify(layout));
  }, [layout, layoutMode]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveFlowIndex((current) => (current + 1) % p6PortalFlows.length);
    }, 2200);

    return () => window.clearInterval(timer);
  }, []);

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
        [currentDrag.nodeId]: clampNodePosition(currentDrag.nodeId, {
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
  }, [camera.scale, dragState]);

  const flowPaths = useMemo(
    () =>
      p6PortalFlows.map((flow) => ({
        ...flow,
        ...createFlowPath(flow, layout),
      })),
    [layout],
  );

  const emphasizedArtifactIds = new Set<(typeof p6PortalArtifacts)[number]["id"]>();

  const emphasizedFlowIds = new Set<string>();
  const emphasizedNodeIds = new Set<P6PortalNodeId>();

  if (focusNodeId) {
    emphasizedNodeIds.add(focusNodeId);
    p6PortalFlows.forEach((flow) => {
      if (flow.from === focusNodeId || flow.to === focusNodeId) {
        emphasizedFlowIds.add(flow.id);
        emphasizedNodeIds.add(flow.from);
        emphasizedNodeIds.add(flow.to);
      }
    });
    p6PortalArtifacts.forEach((artifact) => {
      if (artifact.linkedNodeIds.includes(focusNodeId)) {
        emphasizedArtifactIds.add(artifact.id);
      }
    });
  } else {
    emphasizedFlowIds.add(activeFlow.id);
    emphasizedNodeIds.add(activeFlow.from);
    emphasizedNodeIds.add(activeFlow.to);
    p6PortalArtifacts.forEach((artifact) => {
      if (artifact.linkedFlowIds.includes(activeFlow.id)) {
        emphasizedArtifactIds.add(artifact.id);
      }
    });
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
    <div id="p6-portal-page" className="p6-portal-page">
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
        <div className="p6-portal-viewport__ambient p6-portal-viewport__ambient--one" />
        <div className="p6-portal-viewport__ambient p6-portal-viewport__ambient--two" />

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
          <div
            data-testid="p6-portal-world-boundary"
            className="p6-portal-stage__boundary"
            style={{
              left: `${P6_PORTAL_NODE_PADDING}px`,
              top: `${P6_PORTAL_NODE_PADDING}px`,
              width: `${P6_PORTAL_WORLD.width - P6_PORTAL_NODE_PADDING * 2}px`,
              height: `${P6_PORTAL_WORLD.height - P6_PORTAL_NODE_PADDING * 2}px`,
            }}
          >
            <span className="p6-portal-stage__boundary-label">自动布局区</span>
            <span className="p6-portal-stage__boundary-note">边界内可拖拽，边界外只保留视口平移</span>
          </div>

          <svg
            className="p6-portal-stage__wires"
            viewBox={`0 0 ${P6_PORTAL_WORLD.width} ${P6_PORTAL_WORLD.height}`}
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            {flowPaths.map((flow, index) => (
              <g key={flow.id}>
                <path
                  d={flow.d}
                  className={[
                    "p6-portal-wire",
                    `p6-portal-wire--${flow.tone}`,
                    `p6-portal-wire--${flow.renderStyle}`,
                    emphasizedFlowIds.has(flow.id) ? "is-emphasized" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                />
                <path
                  d={flow.d}
                  className={[
                    "p6-portal-wire-travel",
                    `p6-portal-wire-travel--${flow.tone}`,
                    `p6-portal-wire-travel--${flow.renderStyle}`,
                    emphasizedFlowIds.has(flow.id) ? "is-emphasized" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  style={{ animationDelay: `${index * 0.35}s` }}
                />
              </g>
            ))}
          </svg>

          {relationshipMode === "semantic"
            ? flowPaths.map((flow) => (
                <div
                  key={`${flow.id}-label`}
                  data-testid={`p6-flow-label-${flow.id}`}
                  className={[
                    "p6-portal-flow-label",
                    `p6-portal-flow-label--${flow.tone}`,
                    `p6-portal-flow-label--${flow.renderStyle}`,
                    emphasizedFlowIds.has(flow.id) ? "is-emphasized" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  title={flow.semanticLabel}
                  style={{
                    left: `${flow.labelPosition.x - 56}px`,
                    top: `${flow.labelPosition.y - 18}px`,
                  }}
                >
                  {flow.label}
                </div>
              ))
            : null}

          {visibleArtifacts.map((artifact) => (
            <P6BlueprintArtifact key={artifact.id} artifact={artifact} emphasized={emphasizedArtifactIds.has(artifact.id)} />
          ))}

          {p6PortalNodes.map((node) => (
            <P6BlueprintNode
              key={node.id}
              node={node}
              position={layout[node.id]}
              active={selectedNodeId === node.id}
              emphasized={emphasizedNodeIds.has(node.id)}
              visiblePins={getVisiblePins(node.id)}
              relationSummary={relationshipMode === "projection" ? relationSnapshots[node.id]?.label : undefined}
              onClick={() => setSelectedNodeId(node.id)}
              onDoubleClick={() => {
                if (node.route) {
                  navigate(node.route);
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
          setCamera(defaultCamera);
          setLayout(layoutMode === "system" ? defaultP6PortalLayout : personalLayoutRef.current);
          setSelectedNodeId("p2");
        }}
      />
    </div>
  );
}
