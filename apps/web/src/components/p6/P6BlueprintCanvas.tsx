import { useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, WheelEvent as ReactWheelEvent } from "react";
import { useNavigate } from "react-router-dom";

import {
  createP6DisplayExperiment,
  getP6DisplayWorkbench,
  type P6DisplayWorkbenchBootstrap,
  type P6MockScenarioCatalog,
  type P6PlatformDisplayBaselinePackage,
  type P6PlatformLegend,
  type P6PlatformRoutes,
  type P6PortalProjection,
  type P6SourceMode,
} from "../../lib/p6";
import { P6BlueprintArtifact } from "./P6BlueprintArtifact";
import { P6ExperimentWorkbench } from "./P6ExperimentWorkbench";
import { P6BlueprintLegend } from "./P6BlueprintLegend";
import { P6BlueprintNode } from "./P6BlueprintNode";
import { buildP6CssVariables } from "./p6Baseline";
import {
  P6_PORTAL_LAYOUT_STORAGE_KEY,
  P6_PORTAL_WORLD,
  type P6PortalAnchorSide,
  type P6PortalNodeId,
  type P6PortalPosition,
  defaultP6PortalLayout,
} from "./p6PortalData";
import {
  P6_PORTAL_NODE_PADDING,
  clampCameraToWorld,
  clampNodePosition,
  getPortalNodeById,
  type P6PortalCameraState as CameraState,
} from "./p6PortalGeometry";
import {
  buildExperimentRecord,
  buildExperimentSavePayload,
  buildExperimentTargetOptions,
  buildBindingPresetOptions,
  buildLayoutPresetOptions,
  buildModuleTemplateOptions,
  buildPreviewEntries,
  buildUserTemplateOptions,
  createDefaultExperimentDraft,
  resolveNodeCard,
  setBindingPreset,
  setModuleTemplate,
  setUserTemplate,
  type P6ExperimentTargetId,
} from "./p6ExperimentConfig";
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
  x: 24,
  y: 36,
  scale: 0.72,
};

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
  const fromNode = getPortalNodeById(nodeIds, flow.from);
  const toNode = getPortalNodeById(nodeIds, flow.to);
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
  const [selectedNodeId, setSelectedNodeId] = useState<P6PortalNodeId | null>("p2");
  const [hoveredNodeId, setHoveredNodeId] = useState<P6PortalNodeId | null>(null);
  const [activeFlowIndex, setActiveFlowIndex] = useState(0);
  const [layoutMode, setLayoutMode] = useState<P6PortalLayoutMode>(() => (hasStoredP6PortalLayout() ? "personal" : "system"));
  const [relationshipMode, setRelationshipMode] = useState<P6PortalRelationshipViewMode>("semantic");
  const [experimentWorkbenchOpen, setExperimentWorkbenchOpen] = useState(false);
  const [experimentDraft, setExperimentDraft] = useState(createDefaultExperimentDraft);
  const [workbenchData, setWorkbenchData] = useState<P6DisplayWorkbenchBootstrap | null>(null);
  const [workbenchLoading, setWorkbenchLoading] = useState(false);
  const [workbenchError, setWorkbenchError] = useState<string | null>(null);
  const [experimentSaving, setExperimentSaving] = useState(false);
  const [experimentSaveError, setExperimentSaveError] = useState<string | null>(null);
  const { nodes, flows, artifacts } = useMemo(() => buildPortalViewModel(projection), [projection]);
  const selectedScenario = scenarioCatalog.items.find((item) => item.scenario_id === selectedScenarioId) ?? scenarioCatalog.items[0];
  const experimentTargetOptions = useMemo(() => buildExperimentTargetOptions(nodes), [nodes]);
  const experimentPreviewEntries = useMemo(() => buildPreviewEntries(nodes, experimentDraft), [experimentDraft, nodes]);
  const moduleTemplateOptions = useMemo(
    () => buildModuleTemplateOptions(workbenchData?.templates ?? []),
    [workbenchData],
  );
  const userTemplateOptions = useMemo(
    () => buildUserTemplateOptions(workbenchData?.templates ?? []),
    [workbenchData],
  );
  const bindingPresetOptions = useMemo(
    () => buildBindingPresetOptions(workbenchData?.bindings ?? []),
    [workbenchData],
  );
  const layoutPresetOptions = useMemo(
    () => buildLayoutPresetOptions(workbenchData?.layouts ?? []),
    [workbenchData],
  );
  const experimentRecord = useMemo(
    () => buildExperimentRecord(nodes, experimentDraft, projection.portal_summary.scenario_label),
    [experimentDraft, nodes, projection.portal_summary.scenario_label],
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
      setSelectedNodeId("p2");
    }
  }, [nodes, selectedNodeId]);

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
        emphasizedNodeIds.add(flow.from);
        emphasizedNodeIds.add(flow.to);
      }
    });
    artifacts.forEach((artifact) => {
      if (artifact.linkedNodeIds.includes(focusNodeId)) {
        emphasizedArtifactIds.add(artifact.id);
      }
    });
  } else if (activeFlow) {
    emphasizedFlowIds.add(activeFlow.id);
    emphasizedNodeIds.add(activeFlow.from);
    emphasizedNodeIds.add(activeFlow.to);
  }

  async function ensureWorkbenchLoaded() {
    if (workbenchLoading || workbenchData) {
      return;
    }

    setWorkbenchLoading(true);
    try {
      const response = await getP6DisplayWorkbench();
      setWorkbenchData(response.data);
      setWorkbenchError(null);
    } catch (loadError) {
      setWorkbenchError(loadError instanceof Error ? loadError.message : "加载实验台配置失败");
    } finally {
      setWorkbenchLoading(false);
    }
  }

  async function handleSaveExperiment() {
    setExperimentSaving(true);
    setExperimentSaveError(null);
    try {
      await createP6DisplayExperiment(
        buildExperimentSavePayload(nodes, experimentDraft, projection.portal_summary.scenario_label),
      );
      const response = await getP6DisplayWorkbench();
      setWorkbenchData(response.data);
    } catch (saveError) {
      setExperimentSaveError(saveError instanceof Error ? saveError.message : "登记实验失败");
    } finally {
      setExperimentSaving(false);
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
        <div className="p6-portal-source-control__actions">
          <button
            type="button"
            className={[
              "p6-portal-source-control__button",
              "p6-portal-source-control__button--minor",
              experimentWorkbenchOpen ? "is-active" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => {
              const nextOpen = !experimentWorkbenchOpen;
              if (nextOpen && selectedNodeId) {
                setExperimentDraft((draft) => ({
                  ...draft,
                  selectedTargetId: selectedNodeId,
                }));
                void ensureWorkbenchLoaded();
              }
              setExperimentWorkbenchOpen(nextOpen);
            }}
          >
            卡片配置
          </button>
        </div>
        {error ? (
          <div className="p6-portal-source-control__error">
            <span>{error}</span>
            <button type="button" className="p6-portal-source-control__retry" onClick={onRetry}>
              重试
            </button>
          </div>
        ) : null}
      </div>

      {experimentWorkbenchOpen && workbenchData ? (
        <P6ExperimentWorkbench
          draft={experimentDraft}
          targetOptions={experimentTargetOptions}
          moduleTemplateOptions={moduleTemplateOptions}
          userTemplateOptions={userTemplateOptions}
          bindingPresetOptions={bindingPresetOptions}
          layoutPresetOptions={layoutPresetOptions}
          previewEntries={experimentPreviewEntries}
          record={experimentRecord}
          savedRecords={workbenchData.experiments}
          promotionCandidates={workbenchData.promotion_candidates}
          saving={experimentSaving}
          saveError={experimentSaveError ?? workbenchError}
          onClose={() => setExperimentWorkbenchOpen(false)}
          onTargetChange={(targetId) =>
            setExperimentDraft((draft) => ({
              ...draft,
              selectedTargetId: targetId as P6ExperimentTargetId,
            }))
          }
          onModuleTemplateChange={(templateId) =>
            setExperimentDraft((draft) => setModuleTemplate(draft, draft.selectedTargetId, templateId))
          }
          onUserTemplateChange={(templateId) => setExperimentDraft((draft) => setUserTemplate(draft, templateId))}
          onBindingPresetChange={(bindingPresetId) =>
            setExperimentDraft((draft) => setBindingPreset(draft, draft.selectedTargetId, bindingPresetId))
          }
          onLayoutPresetChange={(layoutPresetId) =>
            setExperimentDraft((draft) => ({
              ...draft,
              layoutPresetId,
            }))
          }
          onPromotionDecisionChange={(decision) =>
            setExperimentDraft((draft) => ({
              ...draft,
              promotionDecision: decision,
            }))
          }
          onTargetStageToggle={(stageId) =>
            setExperimentDraft((draft) => ({
              ...draft,
              targetStages: draft.targetStages.includes(stageId)
                ? draft.targetStages.filter((item) => item !== stageId)
                : [...draft.targetStages, stageId],
            }))
          }
          onSave={() => {
            void handleSaveExperiment();
          }}
        />
      ) : experimentWorkbenchOpen ? (
        <aside data-testid="p6-experiment-workbench" className="p6-experiment-workbench">
          <div className="p6-experiment-workbench__topline">
            <div>
              <div className="p6-experiment-workbench__badge">P6.4</div>
              <h2 className="p6-experiment-workbench__title">卡片配置实验台</h2>
            </div>
            <button type="button" className="p6-experiment-workbench__close" onClick={() => setExperimentWorkbenchOpen(false)}>
              收起
            </button>
          </div>
          <div className="p6-experiment-workbench__section">
            <div className="p6-experiment-workbench__section-title">{workbenchLoading ? "正在加载实验台配置" : workbenchError ?? "实验台暂不可用"}</div>
          </div>
        </aside>
      ) : null}

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

          {nodes.map((node) => (
            <P6BlueprintNode
              key={node.id}
              node={node}
              position={layout[node.id]}
              active={selectedNodeId === node.id}
              emphasized={emphasizedNodeIds.has(node.id)}
              visiblePins={getVisiblePins(flows, node.id)}
              relationSummary={relationshipMode === "projection" ? relationSnapshots[node.id]?.label : undefined}
              cardPresentation={resolveNodeCard(node, experimentDraft)}
              onClick={() => {
                setSelectedNodeId(node.id);
                if (experimentWorkbenchOpen) {
                  setExperimentDraft((draft) => ({
                    ...draft,
                    selectedTargetId: node.id,
                  }));
                }
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
          setCamera(defaultCamera);
          setLayout(layoutMode === "system" ? defaultP6PortalLayout : personalLayoutRef.current);
          setSelectedNodeId("p2");
        }}
      />
    </div>
  );
}
