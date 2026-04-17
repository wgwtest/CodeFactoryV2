import { useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, WheelEvent as ReactWheelEvent } from "react";
import { useNavigate } from "react-router-dom";

import { P6BlueprintLegend } from "./P6BlueprintLegend";
import { P6BlueprintNode } from "./P6BlueprintNode";
import {
  P6_PORTAL_LAYOUT_STORAGE_KEY,
  P6_PORTAL_WORLD,
  type P6PortalAnchorSide,
  type P6PortalFlow,
  type P6PortalNode,
  type P6PortalNodeId,
  type P6PortalPosition,
  defaultP6PortalLayout,
  p6PortalFlows,
  p6PortalNodes,
  readP6PortalLayout,
} from "./p6PortalData";

type CameraState = {
  x: number;
  y: number;
  scale: number;
};

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

function getNodeById(nodeId: P6PortalNodeId) {
  return p6PortalNodes.find((item) => item.id === nodeId) ?? p6PortalNodes[0];
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
  const fromNode = getNodeById(flow.from);
  const toNode = getNodeById(flow.to);
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
  const [layout, setLayout] = useState<Record<P6PortalNodeId, P6PortalPosition>>(() => readP6PortalLayout());
  const [camera, setCamera] = useState<CameraState>(defaultCamera);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<P6PortalNodeId | null>("p2");
  const [hoveredNodeId, setHoveredNodeId] = useState<P6PortalNodeId | null>(null);
  const [activeFlowIndex, setActiveFlowIndex] = useState(0);

  const focusNodeId = hoveredNodeId ?? selectedNodeId;
  const activeFlow = p6PortalFlows[activeFlowIndex] ?? p6PortalFlows[0];

  useEffect(() => {
    window.localStorage.setItem(P6_PORTAL_LAYOUT_STORAGE_KEY, JSON.stringify(layout));
  }, [layout]);

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
        setCamera({
          x: currentDrag.origin.x + event.clientX - currentDrag.startClientX,
          y: currentDrag.origin.y + event.clientY - currentDrag.startClientY,
          scale: currentDrag.origin.scale,
        });
        return;
      }

      const nextX = currentDrag.origin.x + (event.clientX - currentDrag.startClientX) / camera.scale;
      const nextY = currentDrag.origin.y + (event.clientY - currentDrag.startClientY) / camera.scale;

      setLayout((current) => ({
        ...current,
        [currentDrag.nodeId]: {
          x: clamp(nextX, 48, P6_PORTAL_WORLD.width - getNodeById(currentDrag.nodeId).width - 48),
          y: clamp(nextY, 48, P6_PORTAL_WORLD.height - getNodeById(currentDrag.nodeId).height - 48),
        },
      }));
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
  } else {
    emphasizedFlowIds.add(activeFlow.id);
    emphasizedNodeIds.add(activeFlow.from);
    emphasizedNodeIds.add(activeFlow.to);
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

    setCamera({
      x: pointerX - worldX * nextScale,
      y: pointerY - worldY * nextScale,
      scale: nextScale,
    });
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
                    emphasizedFlowIds.has(flow.id) ? "is-emphasized" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  style={{ animationDelay: `${index * 0.35}s` }}
                />
              </g>
            ))}
          </svg>

          {flowPaths.map((flow) => (
            <div
              key={`${flow.id}-label`}
              className={[
                "p6-portal-flow-label",
                `p6-portal-flow-label--${flow.tone}`,
                emphasizedFlowIds.has(flow.id) ? "is-emphasized" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              style={{
                left: `${flow.labelPosition.x - 56}px`,
                top: `${flow.labelPosition.y - 18}px`,
              }}
            >
              {flow.label}
            </div>
          ))}

          <div className="p6-portal-artifact p6-portal-artifact--spec" style={{ left: "745px", top: "300px" }}>
            需求规格说明
          </div>
          <div className="p6-portal-artifact p6-portal-artifact--design" style={{ left: "1180px", top: "330px" }}>
            软件设计说明
          </div>
          <div className="p6-portal-artifact p6-portal-artifact--tooling" style={{ left: "1350px", top: "610px" }}>
            工具化描述 / 调用编排
          </div>

          {p6PortalNodes.map((node) => (
            <P6BlueprintNode
              key={node.id}
              node={node}
              position={layout[node.id]}
              active={selectedNodeId === node.id}
              emphasized={emphasizedNodeIds.has(node.id)}
              visiblePins={getVisiblePins(node.id)}
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
        onResetView={(event) => {
          event.stopPropagation();
          setCamera(defaultCamera);
          setLayout(defaultP6PortalLayout);
          setSelectedNodeId("p2");
        }}
      />
    </div>
  );
}
