import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent as ReactWheelEvent,
} from "react";
import { Button, Input, Tree } from "antd";
import type { DataNode } from "antd/es/tree";
import { A4DocumentSurface } from "./A4DocumentSurface";
import type { StandardDocumentBlockViewModel, StandardDocumentSectionViewModel } from "./models";
import { resolveCanvasStageRenderer, type DesignMorphCanvasStageKind } from "./designMorphRenderers";
import "./design-morph-canvas.css";

export type DesignMorphStageEntityType =
  | "requirement_specification"
  | "software_design_document"
  | "software_function_tree"
  | "software_layered_architecture"
  | "technical_implementation"
  | "presentation_shape"
  | "module_workorder_projection";

export type DesignMorphStageViewModel = {
  id: string;
  entityType: DesignMorphStageEntityType;
  layoutKind: DesignMorphCanvasStageKind;
  title: string;
  subtitle: string;
  summary: string;
  items: string[];
  sourceRefs: string[];
  constraintSummary: string;
  document?: DesignMorphDocumentViewModel;
  functionTree?: FunctionTreeViewModel;
};

export type FunctionTreeOrigin = "converter" | "derived" | "empty";

export type FunctionTreeNodeType =
  | "root"
  | "module"
  | "capability"
  | "function"
  | "interface"
  | "data"
  | "state"
  | "quality"
  | "trace";

export type FunctionTreeNodeViewModel = {
  nodeId: string;
  title: string;
  nodeType: FunctionTreeNodeType;
  status: string;
  moduleId?: string;
  sourceRefs: string[];
  designRefs: string[];
  architectureRefs: string[];
  p4Refs: string[];
  description?: string;
  children: FunctionTreeNodeViewModel[];
  supportingNodes?: FunctionTreeNodeViewModel[];
};

export type FunctionTreeViewModel = {
  treeId: string;
  title: string;
  origin: FunctionTreeOrigin;
  summary: {
    nodeCount: number;
    tracedNodeCount: number;
    pendingNodeCount: number;
    maxDepth: number;
  };
  root: FunctionTreeNodeViewModel | null;
};

export type DesignMorphDocumentSectionViewModel = {
  sectionId: string;
  title: string;
  content: string;
  status?: string;
};

export type DesignMorphDocumentViewModel = {
  title: string;
  subtitle?: string;
  headerLeft: string;
  headerRight: string;
  footerLeft: string;
  footerRight?: string;
  ariaLabel: string;
  emptyDescription: string;
  busyState?: {
    title: string;
    description: string;
    detail?: string;
    elapsedLabel?: string;
    estimateLabel?: string;
    testId?: string;
  };
  structuredSections?: StandardDocumentSectionViewModel[];
  sections: DesignMorphDocumentSectionViewModel[];
};

export type DesignMorphWindowViewModel = {
  id: string;
  title: string;
  fromStageId: string;
  toStageId: string;
};

export type DesignMorphSelectableKind =
  | "stage"
  | "stage_relation"
  | "requirement_section"
  | "requirement_clause"
  | "design_section"
  | "design_block"
  | "function_node"
  | "architecture_layer"
  | "architecture_module"
  | "technical_mapping"
  | "presentation_shape"
  | "projection_node";

export type DesignMorphSelectionAction = {
  actionId: string;
  label: string;
  description?: string;
  disabled?: boolean;
  commandHint?: string;
};

export type DesignMorphSelection = {
  stageId: string;
  objectId: string;
  kind: DesignMorphSelectableKind;
  title: string;
  summary?: string;
  status?: string;
  sourceRefs: string[];
  qualityRefs?: string[];
  actions: DesignMorphSelectionAction[];
  payload?: Record<string, unknown>;
};

type CanvasViewportState = {
  x: number;
  y: number;
  scale: number;
};

type CanvasStageLayoutState = {
  x: number;
  y: number;
  w: number;
  h: number;
};

type MorphCanvasItem = DesignMorphStageViewModel & {
  index: number;
  x: number;
  y: number;
  w: number;
  h: number;
};

type SelectableDocumentSection = {
  section_id: string;
  title: string;
  status?: string;
  blocks: StandardDocumentBlockViewModel[];
};

type DocumentOutlineEntry = {
  sectionId: string;
  title: string;
  level: number;
  firstBlock?: StandardDocumentBlockViewModel;
  section: SelectableDocumentSection;
};

type TrackViewportFrameInput = {
  height: number;
  items: Pick<MorphCanvasItem, "x" | "w">[];
  left: number;
  right: number;
  viewport: CanvasViewportState;
  width: number;
};

type TrackStageLandmarkInput = {
  items: Array<Pick<MorphCanvasItem, "id" | "title" | "x" | "w">>;
  left: number;
  right: number;
};

type RelationGeometryItem = Pick<MorphCanvasItem, "x" | "y" | "w" | "h">;

export type RelationArrowGeometry = {
  start: { x: number; y: number };
  controlStart: { x: number; y: number };
  controlEnd: { x: number; y: number };
  shaftEnd: { x: number; y: number };
  tip: { x: number; y: number };
  baseCenter: { x: number; y: number };
  baseLeft: { x: number; y: number };
  baseRight: { x: number; y: number };
  labelCenter: { x: number; y: number };
};

export type TrackViewportFrame = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type TrackStageLandmark = {
  id: string;
  title: string;
  center: number;
  x: number;
  width: number;
};

export type TrackStageStyle = {
  fill: string;
  stroke: string;
  marker: string;
  text: string;
};

type DragState = {
  pointerId: number | null;
  source: "mouse" | "pointer";
  sx: number;
  sy: number;
  vx: number;
  vy: number;
  moved: boolean;
};

type NodeDragMode = "move" | "resize";

type NodeDragState = {
  pointerId: number | null;
  source: "mouse" | "pointer";
  stageId: string;
  mode: NodeDragMode;
  sx: number;
  sy: number;
  startItem: Pick<MorphCanvasItem, "x" | "y" | "w" | "h">;
  moved: boolean;
};

type TrackDragMode = "move" | "resize-left" | "resize-right";

type TrackMetrics = {
  frame: TrackViewportFrame;
  left: number;
  mainHeight: number;
  mainWidth: number;
  rect: DOMRect;
  right: number;
  worldLeft: number;
  worldRight: number;
  worldWidth: number;
};

type TrackDragState = {
  mode: TrackDragMode;
  pointerId: number | null;
  source: "mouse" | "pointer";
  startClientX: number;
  startLeftWorld: number;
  startRightWorld: number;
  startViewport: CanvasViewportState;
  metrics: TrackMetrics;
};

type DocumentDragMode = "move" | "resize";

type DocumentDragState = {
  mode: DocumentDragMode;
  pointerId: number | null;
  source: "pointer";
  stageId: string;
  startClientX: number;
  startClientY: number;
  startLayout: Pick<MorphCanvasItem, "x" | "y" | "w" | "h">;
};

type DocumentOutlineResizeState = {
  pointerId: number;
  startClientX: number;
  startWidth: number;
};

type DesignMorphCanvasPlatformProps = {
  stages: DesignMorphStageViewModel[];
  windows: DesignMorphWindowViewModel[];
  activeWindowId: string;
  onActiveWindowChange: (windowId: string) => void;
  selectedMorphObjectId?: string | null;
  onSelectMorphObject?: (selection: DesignMorphSelection) => void;
};

type SavedCanvasLayoutSnapshot = {
  activeWindowId: string;
  stageLayouts: Record<string, CanvasStageLayoutState>;
  viewport: CanvasViewportState;
};

type SavedCanvasLayoutRecord = {
  id: string;
  name: string;
  createdAt: string;
  snapshot: SavedCanvasLayoutSnapshot;
};

const MIN_CANVAS_SCALE = 0.42;
const MAX_CANVAS_SCALE = 1.65;
const MIN_STAGE_NODE_WIDTH = 360;
const MIN_STAGE_NODE_HEIGHT = 360;
const STAGE_NODE_TITLE_BAR_HEIGHT = 168;
const STAGE_NODE_RESIZE_HIT_SIZE = 40;
const STAGE_NODE_CONTROL_OUTSET = 72;
const STAGE_RELATION_HIT_WIDTH = 24;
const TRACK_PADDING_X = 36;
const TRACK_HANDLE_HIT_WIDTH = 16;
const SAVED_LAYOUT_STORAGE_KEY = "p3-design-morph-layouts";
const DOCUMENT_OUTLINE_DEFAULT_WIDTH = 172;
const DOCUMENT_OUTLINE_MIN_WIDTH = 120;
const DOCUMENT_OUTLINE_MAX_WIDTH = 260;
const TRACK_STAGE_STYLES: TrackStageStyle[] = [
  { fill: "#2E8C7D", stroke: "#17695D", marker: "#E9FFF9", text: "#174F47" },
  { fill: "#14536B", stroke: "#0B3B50", marker: "#E7F8FF", text: "#123E52" },
  { fill: "#69A84F", stroke: "#437D34", marker: "#F2FFE9", text: "#315D28" },
  { fill: "#D59B32", stroke: "#9D6E19", marker: "#FFF3D4", text: "#6E4E19" },
  { fill: "#2F77BD", stroke: "#1E5790", marker: "#EAF5FF", text: "#214E78" },
  { fill: "#7567D8", stroke: "#5147A8", marker: "#F1EFFF", text: "#443C92" },
  { fill: "#C4546F", stroke: "#97364F", marker: "#FFF0F4", text: "#7D2F44" },
];
const INITIAL_VIEWPORT: CanvasViewportState = { x: -314, y: -3, scale: 0.9 };
const STAGE_LAYOUTS = [
  { x: 80, y: 120, w: 500, h: 640 },
  { x: 720, y: 120, w: 520, h: 640 },
  { x: 1380, y: 140, w: 520, h: 520 },
  { x: 2080, y: 60, w: 1180, h: 820 },
  { x: 3460, y: 150, w: 560, h: 560 },
  { x: 4200, y: 120, w: 560, h: 600 },
  { x: 4920, y: 150, w: 560, h: 520 },
] as const;

export function DesignMorphCanvasPlatform({
  stages,
  windows,
  activeWindowId,
  onActiveWindowChange,
  selectedMorphObjectId,
  onSelectMorphObject,
}: DesignMorphCanvasPlatformProps) {
  const trackCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const mainCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const nodeDragRef = useRef<NodeDragState | null>(null);
  const trackDragRef = useRef<TrackDragState | null>(null);
  const documentDragRef = useRef<DocumentDragState | null>(null);
  const itemsRef = useRef<MorphCanvasItem[]>([]);
  const lastAutoCenteredWindowKeyRef = useRef<string | null>(null);
  const suppressedAutoCenterWindowKeyRef = useRef<string | null>(null);
  const [viewport, setViewport] = useState<CanvasViewportState>(INITIAL_VIEWPORT);
  const [selectedStageId, setSelectedStageId] = useState(stages[1]?.id ?? stages[0]?.id ?? "");
  const [localSelectedObjectId, setLocalSelectedObjectId] = useState<string | null>(activeWindowId);
  const [layoutRevision, setLayoutRevision] = useState(0);
  const [stageLayouts, setStageLayouts] = useState<Record<string, CanvasStageLayoutState>>(() => buildCanvasLayoutState(stages));
  const [savedLayouts, setSavedLayouts] = useState<SavedCanvasLayoutRecord[]>(() => loadSavedCanvasLayouts());
  const [selectedSavedLayoutId, setSelectedSavedLayoutId] = useState("");
  const items = useMemo(() => buildCanvasItems(stages, stageLayouts), [stageLayouts, stages]);
  const activePairIndex = Math.max(0, windows.findIndex((window) => window.id === activeWindowId));
  const activeWindow = windows[activePairIndex] ?? windows[0];
  const activeWindowKey = activeWindow ? buildActiveWindowKey(activeWindow, activePairIndex) : "none";
  const selectedItem = items.find((item) => item.id === selectedStageId) ?? items[1] ?? items[0];
  const effectiveSelectedObjectId = selectedMorphObjectId ?? localSelectedObjectId;
  const selectedRelationId = windows.some((window) => window.id === effectiveSelectedObjectId) ? effectiveSelectedObjectId : null;
  const selectedRelationTitle = selectedRelationId ? windows.find((window) => window.id === selectedRelationId)?.title : null;
  const selectedBlockId = selectedRelationId ? null : effectiveSelectedObjectId;

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  useEffect(() => {
    setStageLayouts((current) => reconcileCanvasLayouts(stages, current));
  }, [stages]);

  useEffect(() => {
    persistSavedCanvasLayouts(savedLayouts);
  }, [savedLayouts]);

  useEffect(() => {
    if (!selectedSavedLayoutId || savedLayouts.some((layout) => layout.id === selectedSavedLayoutId)) {
      return;
    }
    setSelectedSavedLayoutId("");
  }, [savedLayouts, selectedSavedLayoutId]);

  useEffect(() => {
    if (!items.length || items.some((item) => item.id === selectedStageId)) {
      return;
    }
    setSelectedStageId(items[1]?.id ?? items[0]?.id ?? "");
  }, [items, selectedStageId]);

  const centerItem = useCallback(
    (stageId: string, scale: number) => {
      const item = itemsRef.current.find((candidate) => candidate.id === stageId);
      if (!item) {
        return;
      }
      const rect = mainCanvasRef.current?.getBoundingClientRect();
      const width = rect?.width || 1190;
      const height = rect?.height || 788;
      setSelectedStageId(stageId);
      setViewport({
        scale,
        x: width / 2 - (item.x + item.w / 2) * scale,
        y: height / 2 - (item.y + item.h / 2) * scale,
      });
    },
    [],
  );

  useEffect(() => {
    const targetStageId = activeWindow?.toStageId ?? items[1]?.id ?? items[0]?.id;
    if (!targetStageId) {
      return;
    }
    if (lastAutoCenteredWindowKeyRef.current === activeWindowKey) {
      return;
    }
    if (suppressedAutoCenterWindowKeyRef.current === activeWindowKey) {
      suppressedAutoCenterWindowKeyRef.current = null;
      lastAutoCenteredWindowKeyRef.current = activeWindowKey;
      return;
    }
    lastAutoCenteredWindowKeyRef.current = activeWindowKey;
    centerItem(targetStageId, activePairIndex === 3 ? 0.72 : 0.9);
  }, [activePairIndex, activeWindow?.toStageId, activeWindowKey, centerItem, items]);

  useEffect(() => {
    const mainCanvas = mainCanvasRef.current;
    const trackCanvas = trackCanvasRef.current;
    if (!mainCanvas || !trackCanvas || typeof ResizeObserver === "undefined") {
      return;
    }
    const observer = new ResizeObserver(() => setLayoutRevision((value) => value + 1));
    observer.observe(mainCanvas);
    observer.observe(trackCanvas);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const mainCanvas = mainCanvasRef.current;
    const trackCanvas = trackCanvasRef.current;
    if (!mainCanvas || !trackCanvas) {
      return;
    }
    if (isJsdomWithNativeCanvas(mainCanvas) || isJsdomWithNativeCanvas(trackCanvas)) {
      return;
    }
    const mainContext = getCanvasContext(mainCanvas);
    const trackContext = getCanvasContext(trackCanvas);
    if (!mainContext || !trackContext) {
      return;
    }
    renderMainCanvas(mainCanvas, mainContext, items, windows, selectedStageId, selectedRelationId, activeWindowId, viewport);
    const mainRect = mainCanvas.getBoundingClientRect();
    renderTrackCanvas(trackCanvas, trackContext, items, activePairIndex, viewport, mainRect.width || 1190);
  }, [activePairIndex, activeWindowId, items, layoutRevision, selectedRelationId, selectedStageId, viewport, windows]);

  function emitMorphSelection(selection: DesignMorphSelection) {
    setLocalSelectedObjectId(selection.objectId);
    onSelectMorphObject?.(selection);
  }

  function selectStageRelation(
    window: DesignMorphWindowViewModel,
    options: { focusDestination?: boolean; recenter?: boolean } = {},
  ) {
    if (options.focusDestination) {
      setSelectedStageId(window.toStageId);
    }
    if (options.recenter === false) {
      const nextPairIndex = Math.max(0, windows.findIndex((candidate) => candidate.id === window.id));
      suppressedAutoCenterWindowKeyRef.current = buildActiveWindowKey(window, nextPairIndex);
    }
    onActiveWindowChange(window.id);
    emitMorphSelection(buildDesignMorphStageRelationSelection(window));
  }

  function selectDocumentBlock(
    item: MorphCanvasItem,
    block: StandardDocumentBlockViewModel,
    section: SelectableDocumentSection,
  ) {
    setSelectedStageId(item.id);
    emitMorphSelection(buildDocumentBlockSelection(item, block, section));
  }

  function selectFunctionTreeNode(item: MorphCanvasItem, node: FunctionTreeNodeViewModel) {
    setSelectedStageId(item.id);
    emitMorphSelection(buildFunctionTreeNodeSelection(item, node));
  }

  function handleTrackPointerDown(event: ReactPointerEvent<HTMLCanvasElement>) {
    beginTrackDrag(event.currentTarget, event.clientX, event.clientY, event.pointerId, "pointer");
    if (trackDragRef.current && typeof event.currentTarget.setPointerCapture === "function" && typeof event.pointerId === "number") {
      event.currentTarget.setPointerCapture(event.pointerId);
    }
  }

  function handleTrackMouseDown(event: ReactMouseEvent<HTMLCanvasElement>) {
    if (event.button !== 0 || trackDragRef.current) {
      return;
    }
    beginTrackDrag(event.currentTarget, event.clientX, event.clientY, null, "mouse");
  }

  function beginTrackDrag(
    canvas: HTMLCanvasElement,
    clientX: number,
    clientY: number,
    pointerId: number | null,
    source: TrackDragState["source"],
  ) {
    const metrics = getTrackMetrics(canvas, mainCanvasRef.current, itemsRef.current, viewport);
    if (!metrics) {
      return;
    }
    const localX = clientX - metrics.rect.left;
    const localY = clientY - metrics.rect.top;
    const mode = hitTrackControl(metrics.frame, localX, localY);
    if (!mode) {
      canvas.style.cursor = "default";
      return;
    }
    canvas.style.cursor = mode === "move" ? "grabbing" : "ew-resize";
    trackDragRef.current = {
      mode,
      pointerId,
      source,
      startClientX: clientX,
      startLeftWorld: -viewport.x / viewport.scale,
      startRightWorld: (-viewport.x + metrics.mainWidth) / viewport.scale,
      startViewport: viewport,
      metrics,
    };
  }

  function handleTrackPointerMove(event: ReactPointerEvent<HTMLCanvasElement>) {
    const drag = trackDragRef.current;
    if (!drag || drag.source !== "pointer" || (drag.pointerId !== null && drag.pointerId !== event.pointerId)) {
      updateTrackCursor(event.currentTarget, event.clientX, event.clientY);
      return;
    }
    applyTrackDrag(drag, event.clientX);
  }

  function handleTrackMouseMove(event: ReactMouseEvent<HTMLCanvasElement>) {
    const drag = trackDragRef.current;
    if (!drag || drag.source !== "mouse") {
      updateTrackCursor(event.currentTarget, event.clientX, event.clientY);
      return;
    }
    applyTrackDrag(drag, event.clientX);
  }

  function handleTrackPointerUp(event: ReactPointerEvent<HTMLCanvasElement>) {
    if (
      trackDragRef.current?.source === "pointer" &&
      (trackDragRef.current.pointerId === null || trackDragRef.current.pointerId === event.pointerId)
    ) {
      trackDragRef.current = null;
    }
    updateTrackCursor(event.currentTarget, event.clientX, event.clientY);
  }

  function handleTrackMouseUp(event: ReactMouseEvent<HTMLCanvasElement>) {
    if (trackDragRef.current?.source === "mouse") {
      trackDragRef.current = null;
    }
    updateTrackCursor(event.currentTarget, event.clientX, event.clientY);
  }

  function handleTrackPointerLeave(event: ReactPointerEvent<HTMLCanvasElement>) {
    if (!trackDragRef.current) {
      event.currentTarget.style.cursor = "default";
    }
  }

  function applyTrackDrag(drag: TrackDragState, clientX: number) {
    const deltaTrackX = clientX - drag.startClientX;
    const deltaWorld = trackDeltaToWorld(deltaTrackX, drag.metrics);
    if (drag.mode === "move") {
      moveViewportFromTrackDrag(drag, deltaWorld);
      return;
    }
    resizeViewportFromTrackDrag(drag, deltaWorld);
  }

  function handleTrackWheel(event: ReactWheelEvent<HTMLCanvasElement>) {
    const metrics = getTrackMetrics(event.currentTarget, mainCanvasRef.current, itemsRef.current, viewport);
    if (!metrics) {
      return;
    }
    const localX = event.clientX - metrics.rect.left;
    const localY = event.clientY - metrics.rect.top;
    if (!hitTrackControl(metrics.frame, localX, localY)) {
      return;
    }
    event.preventDefault();
    const visibleCenterX = (-viewport.x + metrics.mainWidth / 2) / viewport.scale;
    const visibleCenterY = (-viewport.y + metrics.mainHeight / 2) / viewport.scale;
    const factor = event.deltaY < 0 ? 1.08 : 0.92;
    const nextScale = clamp(viewport.scale * factor, MIN_CANVAS_SCALE, MAX_CANVAS_SCALE);
    setViewport({
      scale: nextScale,
      x: metrics.mainWidth / 2 - visibleCenterX * nextScale,
      y: metrics.mainHeight / 2 - visibleCenterY * nextScale,
    });
  }

  function updateTrackCursor(canvas: HTMLCanvasElement, clientX: number, clientY: number) {
    const metrics = getTrackMetrics(canvas, mainCanvasRef.current, itemsRef.current, viewport);
    if (!metrics) {
      canvas.style.cursor = "default";
      return;
    }
    const localX = clientX - metrics.rect.left;
    const localY = clientY - metrics.rect.top;
    const mode = hitTrackControl(metrics.frame, localX, localY);
    canvas.style.cursor = mode === "move" ? "grab" : mode ? "ew-resize" : "default";
  }

  function moveViewportFromTrackDrag(drag: TrackDragState, deltaWorld: number) {
    const visibleWorldWidth = drag.startRightWorld - drag.startLeftWorld;
    const nextLeft = clampVisibleWorldLeft(drag.startLeftWorld + deltaWorld, visibleWorldWidth, drag.metrics);
    setViewport(buildViewportFromVisibleRange(drag.startViewport, drag.metrics, nextLeft, visibleWorldWidth));
  }

  function resizeViewportFromTrackDrag(drag: TrackDragState, deltaWorld: number) {
    const minVisibleWorldWidth = drag.metrics.mainWidth / MAX_CANVAS_SCALE;
    const maxVisibleWorldWidth = drag.metrics.mainWidth / MIN_CANVAS_SCALE;
    const startWidth = drag.startRightWorld - drag.startLeftWorld;
    const nextWidth =
      drag.mode === "resize-left"
        ? clamp(startWidth - deltaWorld, minVisibleWorldWidth, maxVisibleWorldWidth)
        : clamp(startWidth + deltaWorld, minVisibleWorldWidth, maxVisibleWorldWidth);
    const nextLeft =
      drag.mode === "resize-left"
        ? clampVisibleWorldLeft(drag.startRightWorld - nextWidth, nextWidth, drag.metrics)
        : clampVisibleWorldLeft(drag.startLeftWorld, nextWidth, drag.metrics);
    setViewport(buildViewportFromVisibleRange(drag.startViewport, drag.metrics, nextLeft, nextWidth));
  }

  function handleMainPointerDown(event: ReactPointerEvent<HTMLCanvasElement>) {
    if (documentDragRef.current) {
      return;
    }
    beginMainDrag(event.currentTarget, event.clientX, event.clientY, event.pointerId, "pointer");
    if (typeof event.currentTarget.setPointerCapture === "function") {
      event.currentTarget.setPointerCapture(event.pointerId);
    }
  }

  function handleMainMouseDown(event: ReactMouseEvent<HTMLCanvasElement>) {
    if (event.button !== 0 || dragRef.current || nodeDragRef.current || documentDragRef.current) {
      return;
    }
    beginMainDrag(event.currentTarget, event.clientX, event.clientY, null, "mouse");
  }

  function beginMainDrag(
    canvas: HTMLCanvasElement,
    clientX: number,
    clientY: number,
    pointerId: number | null,
    source: DragState["source"],
  ) {
    const point = canvasPoint(canvas, clientX, clientY);
    const world = screenToWorld(point, viewport);
    const nodeHit = hitTestNodeControl(itemsRef.current, world);
    if (nodeHit) {
      setSelectedStageId(nodeHit.item.id);
      canvas.style.cursor = nodeHit.mode === "resize" ? "nwse-resize" : "move";
      nodeDragRef.current = {
        pointerId,
        source,
        stageId: nodeHit.item.id,
        mode: nodeHit.mode,
        sx: clientX,
        sy: clientY,
        startItem: { x: nodeHit.item.x, y: nodeHit.item.y, w: nodeHit.item.w, h: nodeHit.item.h },
        moved: false,
      };
      return;
    }
    dragRef.current = {
      pointerId,
      source,
      sx: clientX,
      sy: clientY,
      vx: viewport.x,
      vy: viewport.y,
      moved: false,
    };
  }

  function handleMainPointerMove(event: ReactPointerEvent<HTMLCanvasElement>) {
    const nodeDrag = nodeDragRef.current;
    if (nodeDrag?.source === "pointer" && (nodeDrag.pointerId === null || nodeDrag.pointerId === event.pointerId)) {
      applyNodeDrag(nodeDrag, event.clientX, event.clientY);
      return;
    }
    const drag = dragRef.current;
    if (!drag || drag.source !== "pointer" || (drag.pointerId !== null && drag.pointerId !== event.pointerId)) {
      updateMainCursor(event.currentTarget, event.clientX, event.clientY);
      return;
    }
    applyViewportDrag(drag, event.clientX, event.clientY);
  }

  function handleMainMouseMove(event: ReactMouseEvent<HTMLCanvasElement>) {
    if (documentDragRef.current) {
      return;
    }
    const nodeDrag = nodeDragRef.current;
    if (nodeDrag?.source === "mouse") {
      applyNodeDrag(nodeDrag, event.clientX, event.clientY);
      return;
    }
    const drag = dragRef.current;
    if (!drag || drag.source !== "mouse") {
      updateMainCursor(event.currentTarget, event.clientX, event.clientY);
      return;
    }
    applyViewportDrag(drag, event.clientX, event.clientY);
  }

  function applyViewportDrag(drag: DragState, clientX: number, clientY: number) {
    const deltaX = clientX - drag.sx;
    const deltaY = clientY - drag.sy;
    drag.moved = drag.moved || Math.abs(deltaX) + Math.abs(deltaY) > 6;
    setViewport((current) => ({ ...current, x: drag.vx + deltaX, y: drag.vy + deltaY }));
  }

  function applyNodeDrag(drag: NodeDragState, clientX: number, clientY: number) {
    const deltaX = clientX - drag.sx;
    const deltaY = clientY - drag.sy;
    const worldDeltaX = deltaX / viewport.scale;
    const worldDeltaY = deltaY / viewport.scale;
    drag.moved = drag.moved || Math.abs(deltaX) + Math.abs(deltaY) > 6;
    setStageLayouts((current) => {
      const nextLayout =
        drag.mode === "resize"
          ? {
              ...drag.startItem,
              w: Math.max(MIN_STAGE_NODE_WIDTH, Math.round(drag.startItem.w + worldDeltaX)),
              h: Math.max(MIN_STAGE_NODE_HEIGHT, Math.round(drag.startItem.h + worldDeltaY)),
            }
          : {
              ...drag.startItem,
              x: Math.round(drag.startItem.x + worldDeltaX),
              y: Math.round(drag.startItem.y + worldDeltaY),
            };
      return { ...current, [drag.stageId]: nextLayout };
    });
  }

  function handleMainPointerUp(event: ReactPointerEvent<HTMLCanvasElement>) {
    if (documentDragRef.current) {
      documentDragRef.current = null;
      return;
    }
    const nodeDrag = nodeDragRef.current;
    if (nodeDrag?.source === "pointer" && (nodeDrag.pointerId === null || nodeDrag.pointerId === event.pointerId)) {
      nodeDragRef.current = null;
      updateMainCursor(event.currentTarget, event.clientX, event.clientY);
      return;
    }
    const drag = dragRef.current;
    if (!drag || drag.source !== "pointer" || (drag.pointerId !== null && drag.pointerId !== event.pointerId)) {
      return;
    }
    finishMainViewportDrag(event.currentTarget, event.clientX, event.clientY, drag);
  }

  function handleMainMouseUp(event: ReactMouseEvent<HTMLCanvasElement>) {
    if (documentDragRef.current) {
      documentDragRef.current = null;
      return;
    }
    const nodeDrag = nodeDragRef.current;
    if (nodeDrag?.source === "mouse") {
      nodeDragRef.current = null;
      updateMainCursor(event.currentTarget, event.clientX, event.clientY);
      return;
    }
    const drag = dragRef.current;
    if (!drag || drag.source !== "mouse") {
      return;
    }
    finishMainViewportDrag(event.currentTarget, event.clientX, event.clientY, drag);
  }

  function finishMainViewportDrag(canvas: HTMLCanvasElement, clientX: number, clientY: number, drag: DragState) {
    dragRef.current = null;
    updateMainCursor(canvas, clientX, clientY);
    if (drag.moved) {
      return;
    }
    const point = canvasPoint(canvas, clientX, clientY);
    const world = screenToWorld(point, viewport);
    const relationHit = hitTestRelation(itemsRef.current, windows, world);
    if (relationHit) {
      selectStageRelation(relationHit, { focusDestination: false, recenter: false });
      return;
    }
    const hit = hitTest(itemsRef.current, world);
    if (hit) {
      setSelectedStageId(hit.id);
    }
  }

  function handleMainPointerLeave(event: ReactPointerEvent<HTMLCanvasElement>) {
    if (documentDragRef.current) {
      documentDragRef.current = null;
    }
    handleMainPointerUp(event);
    if (!dragRef.current && !nodeDragRef.current) {
      event.currentTarget.style.cursor = "grab";
    }
  }

  function handleMainMouseLeave(event: ReactMouseEvent<HTMLCanvasElement>) {
    if (documentDragRef.current) {
      documentDragRef.current = null;
    }
    if (nodeDragRef.current?.source === "mouse") {
      nodeDragRef.current = null;
    }
    if (dragRef.current?.source === "mouse") {
      dragRef.current = null;
    }
    event.currentTarget.style.cursor = "grab";
  }

  function updateMainCursor(canvas: HTMLCanvasElement, clientX: number, clientY: number) {
    if (dragRef.current || nodeDragRef.current) {
      return;
    }
    const point = canvasPoint(canvas, clientX, clientY);
    const world = screenToWorld(point, viewport);
    const hit = hitTestNodeControl(itemsRef.current, world);
    if (hit) {
      canvas.style.cursor = hit.mode === "resize" ? "nwse-resize" : "move";
      return;
    }
    canvas.style.cursor = hitTestRelation(itemsRef.current, windows, world) ? "pointer" : "grab";
  }

  function handleWheel(event: ReactWheelEvent<HTMLCanvasElement>) {
    if (documentDragRef.current) {
      return;
    }
    event.preventDefault();
    const point = canvasPoint(event.currentTarget, event.clientX, event.clientY);
    const before = screenToWorld(point, viewport);
    const factor = event.deltaY < 0 ? 1.08 : 0.92;
    const nextScale = clamp(viewport.scale * factor, MIN_CANVAS_SCALE, MAX_CANVAS_SCALE);
    setViewport({
      scale: nextScale,
      x: point.x - before.x * nextScale,
      y: point.y - before.y * nextScale,
    });
  }

  function moveWindow(delta: number) {
    const nextWindow = windows[Math.max(0, Math.min(windows.length - 1, activePairIndex + delta))];
    if (nextWindow) {
      selectStageRelation(nextWindow, { focusDestination: true, recenter: true });
    }
  }

  function fitViewport() {
    setViewport({ scale: 0.44, x: 30, y: 120 });
  }

  function centerLargeArchitecture() {
    centerItem(stages[3]?.id ?? items[3]?.id ?? selectedStageId, 0.62);
  }

  function recordCurrentLayout() {
    const nextIndex = getNextSavedLayoutIndex(savedLayouts);
    const nextLayout: SavedCanvasLayoutRecord = {
      id: `layout-${nextIndex}`,
      name: `布局 ${nextIndex}`,
      createdAt: new Date().toISOString(),
      snapshot: buildSavedCanvasLayoutSnapshot(activeWindowId, stageLayouts, viewport),
    };
    setSavedLayouts((current) => [...current, nextLayout]);
    setSelectedSavedLayoutId(nextLayout.id);
  }

  function applySavedLayout(layoutId: string) {
    setSelectedSavedLayoutId(layoutId);
    const savedLayout = savedLayouts.find((layout) => layout.id === layoutId);
    if (!savedLayout) {
      return;
    }
    setStageLayouts(reconcileCanvasLayouts(stages, savedLayout.snapshot.stageLayouts));
    setViewport(savedLayout.snapshot.viewport);
    const nextWindow = windows.find((window) => window.id === savedLayout.snapshot.activeWindowId);
    if (nextWindow) {
      const nextPairIndex = Math.max(0, windows.findIndex((window) => window.id === nextWindow.id));
      suppressedAutoCenterWindowKeyRef.current = buildActiveWindowKey(nextWindow, nextPairIndex);
      onActiveWindowChange(nextWindow.id);
      emitMorphSelection(buildDesignMorphStageRelationSelection(nextWindow));
    }
  }

  function deleteSelectedSavedLayout() {
    const savedLayout = savedLayouts.find((layout) => layout.id === selectedSavedLayoutId);
    if (!savedLayout) {
      return;
    }
    if (!window.confirm(`删除布局“${savedLayout.name}”？`)) {
      return;
    }
    setSavedLayouts((current) => current.filter((layout) => layout.id !== selectedSavedLayoutId));
    setSelectedSavedLayoutId("");
  }

  function beginDocumentDrag(
    stageId: string,
    mode: DocumentDragMode,
    clientX: number,
    clientY: number,
    pointerId: number,
  ) {
    documentDragRef.current = {
      mode,
      pointerId,
      source: "pointer",
      stageId,
      startClientX: clientX,
      startClientY: clientY,
      startLayout: {
        x: itemsRef.current.find((item) => item.id === stageId)?.x ?? 0,
        y: itemsRef.current.find((item) => item.id === stageId)?.y ?? 0,
        w: itemsRef.current.find((item) => item.id === stageId)?.w ?? 0,
        h: itemsRef.current.find((item) => item.id === stageId)?.h ?? 0,
      },
    };
    setSelectedStageId(stageId);
  }

  function handleDocumentDragMove(
    stageId: string,
    mode: DocumentDragMode,
    clientX: number,
    clientY: number,
    pointerId: number,
  ) {
    const drag = documentDragRef.current;
    if (!drag || drag.stageId !== stageId || drag.mode !== mode || drag.pointerId !== pointerId) {
      return;
    }
    const deltaX = (clientX - drag.startClientX) / viewport.scale;
    const deltaY = (clientY - drag.startClientY) / viewport.scale;
    setStageLayouts((current) => {
      const start = drag.startLayout;
      const nextLayout =
        mode === "resize"
          ? {
              ...start,
              w: Math.max(MIN_STAGE_NODE_WIDTH, Math.round(start.w + deltaX)),
              h: Math.max(MIN_STAGE_NODE_HEIGHT, Math.round(start.h + deltaY)),
            }
          : {
              ...start,
              x: Math.round(start.x + deltaX),
              y: Math.round(start.y + deltaY),
            };
      return { ...current, [stageId]: nextLayout };
    });
  }

  return (
    <div className="design-morph-platform" data-testid="design-morph-canvas-platform">
      <div className="design-morph-semantic-model" data-testid="design-morph-semantic-model">
        {items.map((item) => (
          <section key={item.id} aria-label={`${item.title} Canvas 语义对象`}>
            <h4>{item.title}</h4>
            <p>{item.summary}</p>
            <ul>
              {item.items.map((entry) => (
                <li key={`${item.id}-${entry}`}>{entry}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>
      <div className="design-morph-track-shell">
        <canvas
          aria-label="软设形态滑窗 Canvas"
          className="design-morph-track-canvas"
          data-testid="design-morph-track-canvas"
          ref={trackCanvasRef}
          onMouseDown={handleTrackMouseDown}
          onMouseMove={handleTrackMouseMove}
          onMouseUp={handleTrackMouseUp}
          onPointerDown={handleTrackPointerDown}
          onPointerLeave={handleTrackPointerLeave}
          onPointerMove={handleTrackPointerMove}
          onPointerUp={handleTrackPointerUp}
          onWheel={handleTrackWheel}
        />
      </div>
      <div className="design-morph-canvas-shell">
        <canvas
          aria-label="软设工作区 Canvas"
          className="design-morph-main-canvas"
          data-testid="design-morph-main-canvas"
          ref={mainCanvasRef}
          onMouseDown={handleMainMouseDown}
          onMouseLeave={handleMainMouseLeave}
          onMouseMove={handleMainMouseMove}
          onMouseUp={handleMainMouseUp}
          onPointerDown={handleMainPointerDown}
          onPointerLeave={handleMainPointerLeave}
          onPointerMove={handleMainPointerMove}
          onPointerUp={handleMainPointerUp}
          onWheel={handleWheel}
        />
        <div className="design-morph-object-layer" data-testid="design-morph-object-layer">
          {items.map((item) =>
            item.document ? (
              <DocumentStageObject
                active={item.id === activeWindow?.fromStageId || item.id === activeWindow?.toStageId}
                item={item}
                key={item.id}
                onDragEnd={() => {
                  documentDragRef.current = null;
                }}
                onDragMove={(stageId, mode, clientX, clientY, pointerId) => {
                  handleDocumentDragMove(stageId, mode, clientX, clientY, pointerId);
                }}
                onDragStart={(stageId, mode, clientX, clientY, pointerId) => {
                  beginDocumentDrag(stageId, mode, clientX, clientY, pointerId);
                }}
                onSelectBlock={selectDocumentBlock}
                selected={item.id === selectedStageId}
                selectedBlockId={selectedBlockId}
                viewport={viewport}
              />
            ) : item.functionTree ? (
              <FunctionTreeStageObject
                active={item.id === activeWindow?.fromStageId || item.id === activeWindow?.toStageId}
                item={item}
                key={item.id}
                onDragEnd={() => {
                  documentDragRef.current = null;
                }}
                onDragMove={(stageId, mode, clientX, clientY, pointerId) => {
                  handleDocumentDragMove(stageId, mode, clientX, clientY, pointerId);
                }}
                onDragStart={(stageId, mode, clientX, clientY, pointerId) => {
                  beginDocumentDrag(stageId, mode, clientX, clientY, pointerId);
                }}
                onSelectNode={selectFunctionTreeNode}
                selected={item.id === selectedStageId}
                selectedNodeId={selectedBlockId}
                viewport={viewport}
              />
            ) : null,
          )}
        </div>
        <div className="design-morph-hud">
          <span>Canvas 窗口：{activeWindow?.title ?? "需规文档 -> 软设文档"}</span>
          <span>缩放 {Math.round(viewport.scale * 100)}%</span>
          <span>
            平移 {Math.round(viewport.x)},{Math.round(viewport.y)}
          </span>
          {selectedItem ? (
            <span>{`节点：${selectedItem.title} @${Math.round(selectedItem.x)},${Math.round(selectedItem.y)} · ${Math.round(
              selectedItem.w,
            )}x${Math.round(selectedItem.h)}`}</span>
          ) : null}
          <span>拖拽空白平移 · 滚轮缩放 · 拖标题栏移动节点 · 右下角缩放节点</span>
        </div>
      </div>
      <footer className="design-morph-controls">
        <span>
          {selectedRelationTitle
            ? `选中关系：${selectedRelationTitle}`
            : selectedStageId
              ? `选中：${items.find((item) => item.id === selectedStageId)?.title ?? selectedStageId}`
              : "选中：-"}
        </span>
        <div>
          <button type="button" onClick={fitViewport}>
            适配视口
          </button>
          <button type="button" onClick={() => moveWindow(-1)}>
            上一窗口
          </button>
          <button type="button" onClick={() => moveWindow(1)}>
            下一窗口
          </button>
          <button type="button" onClick={centerLargeArchitecture}>
            定位大型架构图
          </button>
          <button type="button" onClick={recordCurrentLayout}>
            记录布局
          </button>
          <label className="design-morph-layout-select">
            <span>使用布局</span>
            <select aria-label="使用布局" value={selectedSavedLayoutId} onChange={(event) => applySavedLayout(event.target.value)}>
              <option value="">选择布局</option>
              {savedLayouts.map((layout) => (
                <option key={layout.id} value={layout.id}>
                  {layout.name}
                </option>
              ))}
            </select>
          </label>
          <button
            aria-label="删除布局"
            className="design-morph-layout-delete"
            disabled={!selectedSavedLayoutId}
            type="button"
            onClick={deleteSelectedSavedLayout}
          >
            ×
          </button>
        </div>
      </footer>
    </div>
  );
}

function DocumentStageObject({
  active,
  item,
  onDragEnd,
  onDragMove,
  onDragStart,
  onSelectBlock,
  selected,
  selectedBlockId,
  viewport,
}: {
  active: boolean;
  item: MorphCanvasItem;
  onDragEnd: () => void;
  onDragMove: (stageId: string, mode: DocumentDragMode, clientX: number, clientY: number, pointerId: number) => void;
  onDragStart: (stageId: string, mode: DocumentDragMode, clientX: number, clientY: number, pointerId: number) => void;
  onSelectBlock: (item: MorphCanvasItem, block: StandardDocumentBlockViewModel, section: SelectableDocumentSection) => void;
  selected: boolean;
  selectedBlockId: string | null;
  viewport: CanvasViewportState;
}) {
  const stageDocument = item.document;
  const [outlineCollapsed, setOutlineCollapsed] = useState(false);
  const [outlineWidth, setOutlineWidth] = useState(DOCUMENT_OUTLINE_DEFAULT_WIDTH);
  const outlineResizeRef = useRef<DocumentOutlineResizeState | null>(null);
  if (!stageDocument) {
    return null;
  }

  const outlineEntries = buildDocumentOutlineEntries(stageDocument.structuredSections);
  const showDocumentOutline = item.entityType === "software_design_document" && outlineEntries.length > 0;
  const documentWorkspaceStyle = showDocumentOutline
    ? ({
        gridTemplateColumns: outlineCollapsed ? "32px minmax(0, 1fr)" : `${outlineWidth}px minmax(0, 1fr)`,
      } satisfies CSSProperties)
    : undefined;

  const objectStyle = {
    transform: `translate(${item.x * viewport.scale + viewport.x}px, ${item.y * viewport.scale + viewport.y}px) scale(${viewport.scale})`,
    transformOrigin: "top left",
    width: `${item.w}px`,
    height: `${item.h}px`,
    zIndex: selected ? 6 : active ? 5 : 4,
  } as const;

  return (
    <section
      className={[
        "design-morph-object-frame",
        "is-document-stage-object",
        selected ? "is-selected" : "",
        active ? "is-active" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      data-testid={`stage-object-${item.id}`}
      style={objectStyle}
    >
      <header
        className="design-morph-object-titlebar"
        data-testid="stage-object-compact-titlebar"
        onPointerDown={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onDragStart(item.id, "move", event.clientX, event.clientY, event.pointerId);
          if (typeof event.currentTarget.setPointerCapture === "function") {
            event.currentTarget.setPointerCapture(event.pointerId);
          }
        }}
        onPointerMove={(event) => {
          onDragMove(item.id, "move", event.clientX, event.clientY, event.pointerId);
        }}
        onPointerUp={(event) => {
          onDragEnd();
          if (typeof event.currentTarget.releasePointerCapture === "function") {
            event.currentTarget.releasePointerCapture(event.pointerId);
          }
        }}
      >
        <div className="design-morph-object-title-copy">
          <span className="design-morph-object-title-row">
            <strong>{item.title}</strong>
            <span className="design-morph-object-title-meta">{item.subtitle}</span>
          </span>
        </div>
      </header>
      <div
        className="design-morph-object-body"
        onMouseDown={(event) => event.stopPropagation()}
        onPointerDown={(event) => event.stopPropagation()}
        onWheel={(event) => event.stopPropagation()}
      >
        <div
          className={[
            "design-morph-document-workspace",
            showDocumentOutline ? "has-document-outline" : "",
            showDocumentOutline && outlineCollapsed ? "is-outline-collapsed" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          data-testid={showDocumentOutline ? "software-design-document-workspace" : undefined}
          style={documentWorkspaceStyle}
        >
          {showDocumentOutline ? (
            <aside
              aria-label="软设文档目录"
              className="design-morph-document-outline"
              data-testid="software-design-document-outline"
            >
              <div className="design-morph-document-outline-header">
                {!outlineCollapsed ? <span>目录</span> : null}
                <button
                  aria-label={outlineCollapsed ? "展开软设目录" : "折叠软设目录"}
                  className="design-morph-document-outline-toggle"
                  type="button"
                  onClick={() => setOutlineCollapsed((value) => !value)}
                >
                  {outlineCollapsed ? "目" : "‹"}
                </button>
              </div>
              {!outlineCollapsed ? (
                <ol className="design-morph-document-outline-list">
                  {outlineEntries.map((entry, index) => (
                    <li key={entry.sectionId}>
                      <button
                        aria-label={`${index + 1} ${entry.title}`}
                        className="design-morph-document-outline-item"
                        style={{ "--outline-indent": `${(entry.level - 1) * 10}px` } as CSSProperties}
                        type="button"
                        onClick={() => {
                          const targetBlock = entry.firstBlock;
                          if (targetBlock) {
                            onSelectBlock(item, targetBlock, entry.section);
                            requestAnimationFrame(() => {
                              const targetElement = globalThis.document.getElementById(
                                targetBlock.anchorId ?? targetBlock.blockId,
                              );
                              if (typeof targetElement?.scrollIntoView === "function") {
                                targetElement.scrollIntoView({ block: "center", behavior: "smooth" });
                              }
                            });
                          }
                        }}
                      >
                        <span>{index + 1}</span>
                        <strong>{entry.title}</strong>
                      </button>
                    </li>
                  ))}
                </ol>
              ) : null}
              {!outlineCollapsed ? (
                <div
                  aria-label="调整软设目录宽度"
                  aria-orientation="vertical"
                  aria-valuemax={DOCUMENT_OUTLINE_MAX_WIDTH}
                  aria-valuemin={DOCUMENT_OUTLINE_MIN_WIDTH}
                  aria-valuenow={outlineWidth}
                  className="design-morph-document-outline-resizer"
                  role="separator"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") {
                      return;
                    }
                    event.preventDefault();
                    event.stopPropagation();
                    const delta = event.key === "ArrowRight" ? 12 : -12;
                    setOutlineWidth((value) =>
                      clamp(value + delta, DOCUMENT_OUTLINE_MIN_WIDTH, DOCUMENT_OUTLINE_MAX_WIDTH),
                    );
                  }}
                  onPointerDown={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    outlineResizeRef.current = {
                      pointerId: event.pointerId,
                      startClientX: event.clientX,
                      startWidth: outlineWidth,
                    };
                    if (typeof event.currentTarget.setPointerCapture === "function") {
                      event.currentTarget.setPointerCapture(event.pointerId);
                    }
                  }}
                  onPointerMove={(event) => {
                    const drag = outlineResizeRef.current;
                    if (!drag || drag.pointerId !== event.pointerId) {
                      return;
                    }
                    event.preventDefault();
                    event.stopPropagation();
                    setOutlineWidth(
                      clamp(
                        drag.startWidth + event.clientX - drag.startClientX,
                        DOCUMENT_OUTLINE_MIN_WIDTH,
                        DOCUMENT_OUTLINE_MAX_WIDTH,
                      ),
                    );
                  }}
                  onPointerUp={(event) => {
                    if (outlineResizeRef.current?.pointerId === event.pointerId) {
                      outlineResizeRef.current = null;
                    }
                    if (typeof event.currentTarget.releasePointerCapture === "function") {
                      event.currentTarget.releasePointerCapture(event.pointerId);
                    }
                  }}
                  onPointerCancel={(event) => {
                    if (outlineResizeRef.current?.pointerId === event.pointerId) {
                      outlineResizeRef.current = null;
                    }
                  }}
                />
              ) : null}
            </aside>
          ) : null}
        <div className="stage-document-scroll design-morph-object-scroll" data-testid="document-stage-scroll">
          <div className="design-morph-object-paper" data-testid="document-stage-paper">
            <A4DocumentSurface
              ariaLabel={stageDocument.ariaLabel}
              busyState={stageDocument.busyState}
              emptyDescription={stageDocument.emptyDescription}
              footerLeft={stageDocument.footerLeft}
              footerRight={stageDocument.footerRight}
              headerLeft={stageDocument.headerLeft}
              headerRight={stageDocument.headerRight}
              onSelectBlock={(block, section) => onSelectBlock(item, block, section)}
              sections={stageDocument.sections.map((section) => ({
                section_id: section.sectionId,
                title: section.title,
                content: section.content,
                status: section.status,
              }))}
              structuredSections={stageDocument.structuredSections}
              selectedBlockId={selectedBlockId ?? undefined}
              scrollMode="parent"
              subtitle={stageDocument.subtitle}
              title={stageDocument.title}
            />
          </div>
        </div>
        </div>
      </div>
      <button
        aria-label={`${item.title} resize`}
        className="design-morph-object-resize"
        type="button"
        onPointerDown={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onDragStart(item.id, "resize", event.clientX, event.clientY, event.pointerId);
          if (typeof event.currentTarget.setPointerCapture === "function") {
            event.currentTarget.setPointerCapture(event.pointerId);
          }
        }}
        onPointerMove={(event) => {
          onDragMove(item.id, "resize", event.clientX, event.clientY, event.pointerId);
        }}
        onPointerUp={(event) => {
          onDragEnd();
          if (typeof event.currentTarget.releasePointerCapture === "function") {
            event.currentTarget.releasePointerCapture(event.pointerId);
          }
        }}
      />
    </section>
  );
}

function FunctionTreeStageObject({
  active,
  item,
  onDragEnd,
  onDragMove,
  onDragStart,
  onSelectNode,
  selected,
  selectedNodeId,
  viewport,
}: {
  active: boolean;
  item: MorphCanvasItem;
  onDragEnd: () => void;
  onDragMove: (stageId: string, mode: DocumentDragMode, clientX: number, clientY: number, pointerId: number) => void;
  onDragStart: (stageId: string, mode: DocumentDragMode, clientX: number, clientY: number, pointerId: number) => void;
  onSelectNode: (item: MorphCanvasItem, node: FunctionTreeNodeViewModel) => void;
  selected: boolean;
  selectedNodeId: string | null;
  viewport: CanvasViewportState;
}) {
  const functionTree = item.functionTree;
  const [searchKeyword, setSearchKeyword] = useState("");
  const [expandedKeys, setExpandedKeys] = useState<string[]>(() => getDefaultExpandedFunctionTreeKeys(functionTree));
  if (!functionTree) {
    return null;
  }

  const treeStructureSignature = useMemo(() => buildFunctionTreeStructureSignature(functionTree), [functionTree]);
  const nodeById = useMemo(() => buildFunctionTreeNodeMap(functionTree.root), [functionTree.root]);
  const filteredRoot = useMemo(
    () => filterFunctionTreeNode(functionTree.root, searchKeyword.trim()),
    [functionTree.root, searchKeyword],
  );
  const treeData = useMemo(() => filteredRoot ? [toFunctionTreeDataNode(filteredRoot)] : [], [filteredRoot]);
  const allKeys = useMemo(() => collectFunctionTreeNodeIds(functionTree.root), [functionTree.root]);
  const visibleKeys = useMemo(() => collectFunctionTreeNodeIds(filteredRoot), [filteredRoot]);

  useEffect(() => {
    setExpandedKeys(getDefaultExpandedFunctionTreeKeys(functionTree));
  }, [treeStructureSignature]);

  useEffect(() => {
    if (!searchKeyword.trim()) {
      return;
    }
    setExpandedKeys(visibleKeys);
  }, [searchKeyword, visibleKeys]);

  const objectStyle = {
    transform: `translate(${item.x * viewport.scale + viewport.x}px, ${item.y * viewport.scale + viewport.y}px) scale(${viewport.scale})`,
    transformOrigin: "top left",
    width: `${item.w}px`,
    height: `${item.h}px`,
    zIndex: selected ? 6 : active ? 5 : 4,
  } as const;

  return (
    <section
      className={[
        "design-morph-object-frame",
        "is-function-tree-stage-object",
        selected ? "is-selected" : "",
        active ? "is-active" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      data-testid={`stage-object-${item.id}`}
      style={objectStyle}
    >
      <header
        className="design-morph-object-titlebar"
        data-testid="stage-object-compact-titlebar"
        onPointerDown={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onDragStart(item.id, "move", event.clientX, event.clientY, event.pointerId);
          if (typeof event.currentTarget.setPointerCapture === "function") {
            event.currentTarget.setPointerCapture(event.pointerId);
          }
        }}
        onPointerMove={(event) => {
          onDragMove(item.id, "move", event.clientX, event.clientY, event.pointerId);
        }}
        onPointerUp={(event) => {
          onDragEnd();
          if (typeof event.currentTarget.releasePointerCapture === "function") {
            event.currentTarget.releasePointerCapture(event.pointerId);
          }
        }}
      >
        <div className="design-morph-object-title-copy">
          <span className="design-morph-object-title-row">
            <strong>{item.title}</strong>
            <span className="design-morph-object-title-meta">{item.subtitle}</span>
          </span>
        </div>
      </header>
      <div
        className="design-morph-object-body"
        onMouseDown={(event) => event.stopPropagation()}
        onPointerDown={(event) => event.stopPropagation()}
        onWheel={(event) => event.stopPropagation()}
      >
        <div className="design-morph-function-tree-shell">
          <div className="design-morph-function-tree-toolbar">
            <Input
              allowClear
              aria-label="搜索功能节点"
              placeholder="搜索功能节点"
              size="small"
              value={searchKeyword}
              onChange={(event) => setSearchKeyword(event.target.value)}
            />
            <Button size="small" onClick={() => setExpandedKeys(allKeys)}>
              展开全部
            </Button>
            <Button size="small" onClick={() => setExpandedKeys([])}>
              收起全部
            </Button>
            <Button
              size="small"
              onClick={() => {
                setSearchKeyword("");
                setExpandedKeys(getDefaultExpandedFunctionTreeKeys(functionTree));
              }}
            >
              重置视图
            </Button>
          </div>
          <div className="design-morph-function-tree-body">
            {treeData.length ? (
              <Tree
                blockNode
                draggable
                expandedKeys={expandedKeys}
                selectedKeys={selectedNodeId ? [selectedNodeId] : []}
                treeData={treeData}
                onExpand={(keys) => setExpandedKeys(keys.map(String))}
                onSelect={(keys) => {
                  const nodeId = String(keys[0] ?? "");
                  const node = nodeById.get(nodeId);
                  if (node) {
                    onSelectNode(item, node);
                  }
                }}
              />
            ) : (
              <div className="design-morph-function-tree-empty">没有匹配的功能节点。</div>
            )}
          </div>
        </div>
      </div>
      <button
        aria-label={`${item.title} resize`}
        className="design-morph-object-resize"
        type="button"
        onPointerDown={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onDragStart(item.id, "resize", event.clientX, event.clientY, event.pointerId);
          if (typeof event.currentTarget.setPointerCapture === "function") {
            event.currentTarget.setPointerCapture(event.pointerId);
          }
        }}
        onPointerMove={(event) => {
          onDragMove(item.id, "resize", event.clientX, event.clientY, event.pointerId);
        }}
        onPointerUp={(event) => {
          onDragEnd();
          if (typeof event.currentTarget.releasePointerCapture === "function") {
            event.currentTarget.releasePointerCapture(event.pointerId);
          }
        }}
      />
    </section>
  );
}

function getDefaultExpandedFunctionTreeKeys(functionTree: FunctionTreeViewModel | undefined): string[] {
  if (!functionTree?.root) {
    return [];
  }
  const allKeys = collectFunctionTreeNodeIds(functionTree.root);
  if (functionTree.summary.nodeCount <= 12) {
    return allKeys;
  }
  return [functionTree.root.nodeId, ...functionTree.root.children.map((node) => node.nodeId)];
}

function collectFunctionTreeNodeIds(root: FunctionTreeNodeViewModel | null): string[] {
  if (!root) {
    return [];
  }
  return [root.nodeId, ...root.children.flatMap((child) => collectFunctionTreeNodeIds(child))];
}

function buildDocumentOutlineEntries(
  sections: StandardDocumentSectionViewModel[] | undefined,
  level = 1,
): DocumentOutlineEntry[] {
  if (!sections?.length) {
    return [];
  }
  return sections.flatMap((section) => {
    const selectableSection = {
      section_id: section.sectionId,
      title: section.title,
      status: section.status,
      blocks: section.blocks,
    };
    const current: DocumentOutlineEntry = {
      sectionId: section.sectionId,
      title: section.title,
      level,
      firstBlock: findFirstDocumentBlock(section),
      section: selectableSection,
    };
    return [current, ...buildDocumentOutlineEntries(section.children, level + 1)];
  });
}

function findFirstDocumentBlock(section: StandardDocumentSectionViewModel): StandardDocumentBlockViewModel | undefined {
  return section.blocks[0] ?? section.children?.map(findFirstDocumentBlock).find(Boolean);
}

function buildFunctionTreeNodeMap(root: FunctionTreeNodeViewModel | null): Map<string, FunctionTreeNodeViewModel> {
  const nodeMap = new Map<string, FunctionTreeNodeViewModel>();
  function visit(node: FunctionTreeNodeViewModel | null) {
    if (!node) {
      return;
    }
    nodeMap.set(node.nodeId, node);
    node.children.forEach(visit);
  }
  visit(root);
  return nodeMap;
}

function filterFunctionTreeNode(
  node: FunctionTreeNodeViewModel | null,
  keyword: string,
): FunctionTreeNodeViewModel | null {
  if (!node) {
    return null;
  }
  if (!keyword) {
    return node;
  }
  const normalizedKeyword = keyword.toLowerCase();
  const matched =
    node.title.toLowerCase().includes(normalizedKeyword) ||
    node.nodeId.toLowerCase().includes(normalizedKeyword) ||
    node.sourceRefs.some((sourceRef) => sourceRef.toLowerCase().includes(normalizedKeyword));
  const children = node.children
    .map((child) => filterFunctionTreeNode(child, keyword))
    .filter((child): child is FunctionTreeNodeViewModel => Boolean(child));
  if (!matched && children.length === 0) {
    return null;
  }
  return { ...node, children };
}

function toFunctionTreeDataNode(node: FunctionTreeNodeViewModel): DataNode {
  return {
    key: node.nodeId,
    title: <span className="design-morph-function-tree-node-title">{node.title}</span>,
    children: node.children.map((child) => toFunctionTreeDataNode(child)),
  };
}

function buildFunctionTreeStructureSignature(functionTree: FunctionTreeViewModel): string {
  return `${functionTree.treeId}:${collectFunctionTreeNodeIds(functionTree.root).join("|")}`;
}

function buildCanvasLayoutState(stages: DesignMorphStageViewModel[]): Record<string, CanvasStageLayoutState> {
  return stages.reduce<Record<string, CanvasStageLayoutState>>((layouts, stage, index) => {
    layouts[stage.id] = getDefaultStageLayout(index);
    return layouts;
  }, {});
}

function reconcileCanvasLayouts(
  stages: DesignMorphStageViewModel[],
  current: Record<string, CanvasStageLayoutState>,
): Record<string, CanvasStageLayoutState> {
  const stageIds = new Set(stages.map((stage) => stage.id));
  let changed = Object.keys(current).some((stageId) => !stageIds.has(stageId));
  const next = stages.reduce<Record<string, CanvasStageLayoutState>>((layouts, stage, index) => {
    const existing = current[stage.id];
    layouts[stage.id] = existing ?? getDefaultStageLayout(index);
    changed = changed || !existing;
    return layouts;
  }, {});
  return changed ? next : current;
}

function getDefaultStageLayout(index: number): CanvasStageLayoutState {
  const layout = STAGE_LAYOUTS[index] ?? {
    x: 80 + index * 680,
    y: 140,
    w: 540,
    h: 560,
  };
  return { x: layout.x, y: layout.y, w: layout.w, h: layout.h };
}

function buildCanvasItems(
  stages: DesignMorphStageViewModel[],
  stageLayouts: Record<string, CanvasStageLayoutState>,
): MorphCanvasItem[] {
  return stages.map((stage, index) => {
    const layout = STAGE_LAYOUTS[index] ?? {
      x: 80 + index * 680,
      y: 140,
      w: 540,
      h: 560,
    };
    return {
      ...stage,
      index,
      x: stageLayouts[stage.id]?.x ?? layout.x,
      y: stageLayouts[stage.id]?.y ?? layout.y,
      w: stageLayouts[stage.id]?.w ?? layout.w,
      h: stageLayouts[stage.id]?.h ?? layout.h,
    };
  });
}

function buildSavedCanvasLayoutSnapshot(
  activeWindowId: string,
  stageLayouts: Record<string, CanvasStageLayoutState>,
  viewport: CanvasViewportState,
): SavedCanvasLayoutSnapshot {
  return {
    activeWindowId,
    stageLayouts: Object.entries(stageLayouts).reduce<Record<string, CanvasStageLayoutState>>((layouts, [stageId, layout]) => {
      layouts[stageId] = { ...layout };
      return layouts;
    }, {}),
    viewport: { ...viewport },
  };
}

function loadSavedCanvasLayouts(): SavedCanvasLayoutRecord[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(SAVED_LAYOUT_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isSavedCanvasLayoutRecord) : [];
  } catch {
    return [];
  }
}

function persistSavedCanvasLayouts(layouts: SavedCanvasLayoutRecord[]) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(SAVED_LAYOUT_STORAGE_KEY, JSON.stringify(layouts));
}

function getNextSavedLayoutIndex(layouts: SavedCanvasLayoutRecord[]) {
  const usedIndexes = layouts
    .map((layout) => Number(layout.id.replace(/^layout-/, "")))
    .filter((value) => Number.isFinite(value));
  return Math.max(0, ...usedIndexes) + 1;
}

function isSavedCanvasLayoutRecord(value: unknown): value is SavedCanvasLayoutRecord {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<SavedCanvasLayoutRecord>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.name === "string" &&
    typeof candidate.createdAt === "string" &&
    isSavedCanvasLayoutSnapshot(candidate.snapshot)
  );
}

function isSavedCanvasLayoutSnapshot(value: unknown): value is SavedCanvasLayoutSnapshot {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<SavedCanvasLayoutSnapshot>;
  return (
    typeof candidate.activeWindowId === "string" &&
    isCanvasViewportState(candidate.viewport) &&
    isRecordObject(candidate.stageLayouts)
  );
}

function isCanvasViewportState(value: unknown): value is CanvasViewportState {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<CanvasViewportState>;
  return typeof candidate.x === "number" && typeof candidate.y === "number" && typeof candidate.scale === "number";
}

function isRecordObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function buildActiveWindowKey(window: DesignMorphWindowViewModel, activePairIndex: number) {
  return `${window.id}:${window.toStageId}:${activePairIndex}`;
}

function renderMainCanvas(
  canvas: HTMLCanvasElement,
  context: CanvasRenderingContext2D,
  items: MorphCanvasItem[],
  windows: DesignMorphWindowViewModel[],
  selectedStageId: string,
  selectedRelationId: string | null,
  activeWindowId: string,
  viewport: CanvasViewportState,
) {
  const { width, height } = prepareCanvas(canvas, context, 1190, 788);
  context.clearRect(0, 0, width, height);
  drawCanvasBackground(context, width, height);
  context.save();
  context.translate(viewport.x, viewport.y);
  context.scale(viewport.scale, viewport.scale);
  windows.forEach((window) => {
    const from = items.find((item) => item.id === window.fromStageId);
    const to = items.find((item) => item.id === window.toStageId);
    if (from && to) {
      drawArrow(context, from, to, {
        active: window.id === activeWindowId,
        selected: window.id === selectedRelationId,
      });
    }
  });
  items.forEach((item) => drawItem(context, item, item.id === selectedStageId));
  context.restore();
}

function renderTrackCanvas(
  canvas: HTMLCanvasElement,
  context: CanvasRenderingContext2D,
  items: MorphCanvasItem[],
  activePairIndex: number,
  viewport: CanvasViewportState,
  mainCanvasWidth: number,
) {
  const { width, height } = prepareCanvas(canvas, context, 1190, 96);
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#f8fbfa";
  context.fillRect(0, 0, width, height);
  if (!items.length) {
    return;
  }

  const left = TRACK_PADDING_X;
  const right = width - 36;
  const y = Math.max(42, height * 0.48);
  const labelY = calculateTrackLabelY(height, y);
  const worldLeft = Math.min(...items.map((item) => item.x));
  const worldRight = Math.max(...items.map((item) => item.x + item.w));
  const worldWidth = Math.max(1, worldRight - worldLeft);

  context.strokeStyle = "#bfd0cc";
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(left, y);
  context.lineTo(right, y);
  context.stroke();

  const viewportFrame = calculateTrackViewportFrame({ height, items, left, right, viewport, width: mainCanvasWidth });
  context.fillStyle = "rgba(40, 118, 111, 0.16)";
  context.strokeStyle = "#143e52";
  context.lineWidth = 2;
  roundRect(context, viewportFrame.x, viewportFrame.y, viewportFrame.width, viewportFrame.height, 8);
  context.fill();
  context.stroke();

  drawTrackHandle(context, viewportFrame.x, viewportFrame.y, viewportFrame.height);
  drawTrackHandle(context, viewportFrame.x + viewportFrame.width, viewportFrame.y, viewportFrame.height);

  const stageLandmarks = calculateTrackStageLandmarks({ items, left, right });
  items.forEach((item, index) => {
    const landmark = stageLandmarks[index];
    if (!landmark) {
      return;
    }
    const stageStyle = resolveTrackStageStyle(item.id, index, activePairIndex);
    const active = index === activePairIndex || index === activePairIndex + 1;
    context.fillStyle = stageStyle.fill;
    context.strokeStyle = stageStyle.stroke;
    context.lineWidth = 2;
    context.beginPath();
    context.rect(landmark.x, y - 8, landmark.width, 16);
    context.fill();
    context.stroke();
    context.fillStyle = stageStyle.marker;
    context.fillRect(landmark.center - 1, y - 4, 2, 8);
    context.fillStyle = active ? "#14211f" : stageStyle.text;
    context.font = "900 12px Microsoft YaHei, sans-serif";
    context.textAlign = "center";
    context.fillText(item.title, landmark.center, labelY);
  });
  context.textAlign = "left";
}

function drawTrackHandle(context: CanvasRenderingContext2D, x: number, y: number, height: number) {
  context.fillStyle = "#143e52";
  roundRect(context, x - 4, y + 8, 8, height - 16, 4);
  context.fill();
  context.strokeStyle = "rgba(255, 255, 255, 0.85)";
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(x - 1.5, y + 19);
  context.lineTo(x - 1.5, y + height - 19);
  context.moveTo(x + 1.5, y + 19);
  context.lineTo(x + 1.5, y + height - 19);
  context.stroke();
}

function getTrackMetrics(
  trackCanvas: HTMLCanvasElement,
  mainCanvas: HTMLCanvasElement | null,
  items: MorphCanvasItem[],
  viewport: CanvasViewportState,
): TrackMetrics | null {
  if (!items.length) {
    return null;
  }
  const rect = trackCanvas.getBoundingClientRect();
  const mainRect = mainCanvas?.getBoundingClientRect();
  const width = rect.width || 1190;
  const height = rect.height || 96;
  const mainWidth = mainRect?.width || 1190;
  const mainHeight = mainRect?.height || 788;
  const left = TRACK_PADDING_X;
  const right = Math.max(left + 1, width - TRACK_PADDING_X);
  const worldLeft = Math.min(...items.map((item) => item.x));
  const worldRight = Math.max(...items.map((item) => item.x + item.w));
  const worldWidth = Math.max(1, worldRight - worldLeft);
  return {
    frame: calculateTrackViewportFrame({ height, items, left, right, viewport, width: mainWidth }),
    left,
    mainHeight,
    mainWidth,
    rect,
    right,
    worldLeft,
    worldRight,
    worldWidth,
  };
}

function hitTrackControl(frame: TrackViewportFrame, localX: number, localY: number): TrackDragMode | null {
  const inFrameY = localY >= frame.y && localY <= frame.y + frame.height;
  if (!inFrameY) {
    return null;
  }
  const nearLeft = Math.abs(localX - frame.x) <= TRACK_HANDLE_HIT_WIDTH;
  const nearRight = Math.abs(localX - (frame.x + frame.width)) <= TRACK_HANDLE_HIT_WIDTH;
  if (nearLeft) {
    return "resize-left";
  }
  if (nearRight) {
    return "resize-right";
  }
  if (localX >= frame.x && localX <= frame.x + frame.width) {
    return "move";
  }
  return null;
}

function buildViewportFromVisibleRange(
  startViewport: CanvasViewportState,
  metrics: TrackMetrics,
  visibleWorldLeft: number,
  visibleWorldWidth: number,
): CanvasViewportState {
  const nextScale = clamp(metrics.mainWidth / visibleWorldWidth, MIN_CANVAS_SCALE, MAX_CANVAS_SCALE);
  const centerY = (-startViewport.y + metrics.mainHeight / 2) / startViewport.scale;
  const nextX = -visibleWorldLeft * nextScale;
  const nextY = metrics.mainHeight / 2 - centerY * nextScale;
  return { x: nextX, y: nextY, scale: nextScale };
}

function trackDeltaToWorld(deltaTrackX: number, metrics: TrackMetrics) {
  return (deltaTrackX / Math.max(1, metrics.right - metrics.left)) * metrics.worldWidth;
}

function clampVisibleWorldLeft(visibleWorldLeft: number, visibleWorldWidth: number, metrics: TrackMetrics) {
  const minLeft = metrics.worldLeft;
  const maxLeft = Math.max(minLeft, metrics.worldRight - visibleWorldWidth);
  return clamp(visibleWorldLeft, minLeft, maxLeft);
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export function calculateTrackViewportFrame({
  height,
  items,
  left,
  right,
  viewport,
  width,
}: TrackViewportFrameInput): TrackViewportFrame {
  if (!items.length) {
    return { x: left, y: 14, width: right - left, height: Math.max(44, height - 30) };
  }
  const worldLeft = Math.min(...items.map((item) => item.x));
  const worldRight = Math.max(...items.map((item) => item.x + item.w));
  const worldWidth = Math.max(1, worldRight - worldLeft);
  const visibleWorldLeft = (-viewport.x) / viewport.scale;
  const visibleWorldRight = (width - viewport.x) / viewport.scale;
  const overviewLeft = left + ((visibleWorldLeft - worldLeft) / worldWidth) * (right - left);
  const overviewRight = left + ((visibleWorldRight - worldLeft) / worldWidth) * (right - left);
  const x = Math.max(left, Math.min(right, overviewLeft));
  const frameRight = Math.max(left, Math.min(right, overviewRight));
  return {
    x,
    y: 14,
    width: Math.max(36, Math.min(right - x, frameRight - x)),
    height: Math.max(48, height - 30),
  };
}

export function calculateTrackStageLandmarks({ items, left, right }: TrackStageLandmarkInput): TrackStageLandmark[] {
  if (!items.length) {
    return [];
  }
  const worldLeft = Math.min(...items.map((item) => item.x));
  const worldRight = Math.max(...items.map((item) => item.x + item.w));
  const worldWidth = Math.max(1, worldRight - worldLeft);
  const trackWidth = Math.max(1, right - left);
  const minLandmarkWidth = Math.min(18, trackWidth);
  return items.map((item) => {
    const itemLeft = left + ((item.x - worldLeft) / worldWidth) * trackWidth;
    const itemRight = left + ((item.x + item.w - worldLeft) / worldWidth) * trackWidth;
    const width = Math.max(minLandmarkWidth, itemRight - itemLeft);
    return {
      id: item.id,
      title: item.title,
      center: itemLeft + (itemRight - itemLeft) / 2,
      x: itemLeft,
      width: Math.min(trackWidth, width),
    };
  });
}

export function calculateTrackLabelY(height: number, axisY: number) {
  return Math.min(height - 18, axisY + 24);
}

export function resolveTrackStageStyle(stageId: string, index: number, activePairIndex: number): TrackStageStyle {
  const baseStyle = TRACK_STAGE_STYLES[index % TRACK_STAGE_STYLES.length];
  const active = index === activePairIndex || index === activePairIndex + 1;
  const completed = index < activePairIndex;
  if (active) {
    return baseStyle;
  }
  if (completed) {
    return {
      fill: softenHexColor(baseStyle.fill, 0.28),
      stroke: baseStyle.stroke,
      marker: baseStyle.marker,
      text: baseStyle.text,
    };
  }
  return {
    fill: softenHexColor(baseStyle.fill, 0.78),
    stroke: softenHexColor(baseStyle.stroke, 0.3),
    marker: baseStyle.stroke,
    text: baseStyle.text,
  };
}

function softenHexColor(hex: string, ratio: number) {
  const normalized = hex.replace("#", "");
  const r = Number.parseInt(normalized.slice(0, 2), 16);
  const g = Number.parseInt(normalized.slice(2, 4), 16);
  const b = Number.parseInt(normalized.slice(4, 6), 16);
  return `#${toHexChannel(r + (255 - r) * ratio)}${toHexChannel(g + (255 - g) * ratio)}${toHexChannel(b + (255 - b) * ratio)}`;
}

function toHexChannel(value: number) {
  return Math.round(value).toString(16).padStart(2, "0").toUpperCase();
}

function prepareCanvas(
  canvas: HTMLCanvasElement,
  context: CanvasRenderingContext2D,
  fallbackWidth: number,
  fallbackHeight: number,
) {
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(1, Math.floor(rect.width || fallbackWidth));
  const height = Math.max(1, Math.floor(rect.height || fallbackHeight));
  const ratio = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
  canvas.width = Math.floor(width * ratio);
  canvas.height = Math.floor(height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { width, height };
}

function getCanvasContext(canvas: HTMLCanvasElement) {
  try {
    return canvas.getContext("2d");
  } catch {
    return null;
  }
}

function isJsdomWithNativeCanvas(canvas: HTMLCanvasElement) {
  const getContext = canvas.getContext as HTMLCanvasElement["getContext"] & { _isMockFunction?: boolean };
  return window.navigator.userAgent.toLowerCase().includes("jsdom") && !getContext._isMockFunction;
}

function drawCanvasBackground(context: CanvasRenderingContext2D, width: number, height: number) {
  context.fillStyle = "#f9fbfa";
  context.fillRect(0, 0, width, height);
  context.strokeStyle = "rgba(20, 62, 82, 0.055)";
  context.lineWidth = 1;
  for (let x = 0; x < width; x += 56) {
    context.beginPath();
    context.moveTo(x, 0);
    context.lineTo(x, height);
    context.stroke();
  }
  for (let y = 0; y < height; y += 56) {
    context.beginPath();
    context.moveTo(0, y);
    context.lineTo(width, y);
    context.stroke();
  }
}

function drawItem(context: CanvasRenderingContext2D, item: MorphCanvasItem, selected: boolean) {
  context.fillStyle = item.layoutKind === "architecture" ? "#fbfcfb" : "#fffdf8";
  context.strokeStyle = selected ? "#143e52" : "#c7d0cb";
  context.lineWidth = selected ? 3 : 1.4;
  roundRect(context, item.x, item.y, item.w, item.h, 8);
  context.fill();
  context.stroke();

  context.fillStyle = selected ? "rgba(20, 62, 82, 0.08)" : "rgba(215, 224, 220, 0.28)";
  roundRect(context, item.x + 1.5, item.y + 1.5, item.w - 3, STAGE_NODE_TITLE_BAR_HEIGHT - 3, 7);
  context.fill();
  context.strokeStyle = "rgba(20, 62, 82, 0.12)";
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(item.x + 18, item.y + STAGE_NODE_TITLE_BAR_HEIGHT);
  context.lineTo(item.x + item.w - 18, item.y + STAGE_NODE_TITLE_BAR_HEIGHT);
  context.stroke();

  context.fillStyle = "#172221";
  context.font = "950 25px Microsoft YaHei, sans-serif";
  const titleX = item.x + 24;
  const titleY = item.y + 44;
  const maxTitleWidth = item.w - 128;
  const titleText = measureClampedCanvasText(context, item.title, maxTitleWidth);
  context.fillText(titleText, titleX, titleY);
  const titleWidth = context.measureText(titleText).width;
  drawCanvasSubtitlePill(context, item.subtitle, titleX + titleWidth + 12, item.y + 22, item.x + item.w - 82, selected);
  context.fillStyle = "#40514d";
  context.font = "14px Microsoft YaHei, sans-serif";
  wrapCanvasText(context, item.summary, item.x + 24, item.y + 96, item.w - 48, 23, 4);
  context.fillStyle = "#60706c";
  context.font = "12px Microsoft YaHei, sans-serif";
  wrapCanvasText(context, item.constraintSummary, item.x + 24, item.y + 162, item.w - 48, 18, 2);

  drawItemControls(context, item, selected);

  resolveCanvasStageRenderer(item.layoutKind)(context, item);
}

function drawItemControls(context: CanvasRenderingContext2D, item: MorphCanvasItem, selected: boolean) {
  const gripX = item.x + item.w - 52;
  const gripY = item.y + 24;
  context.fillStyle = selected ? "#143e52" : "#edf2f0";
  context.strokeStyle = selected ? "#143e52" : "#b6c6c1";
  context.lineWidth = 1.4;
  roundRect(context, gripX, gripY, 28, 28, 7);
  context.fill();
  context.stroke();
  context.strokeStyle = selected ? "rgba(255, 255, 255, 0.86)" : "#81918d";
  context.lineWidth = 1.5;
  for (let index = 0; index < 3; index += 1) {
    const y = gripY + 9 + index * 5;
    context.beginPath();
    context.moveTo(gripX + 8, y);
    context.lineTo(gripX + 20, y);
    context.stroke();
  }

  const resizeX = item.x + item.w - 34;
  const resizeY = item.y + item.h - 34;
  context.fillStyle = selected ? "rgba(20, 62, 82, 0.1)" : "rgba(255, 255, 255, 0.88)";
  context.strokeStyle = selected ? "#143e52" : "#9eafaa";
  context.lineWidth = 1.4;
  roundRect(context, resizeX, resizeY, 24, 24, 6);
  context.fill();
  context.stroke();
  context.strokeStyle = selected ? "#143e52" : "#748481";
  context.lineWidth = 1.6;
  [0, 6, 12].forEach((offset) => {
    context.beginPath();
    context.moveTo(resizeX + 8 + offset, resizeY + 20);
    context.lineTo(resizeX + 20, resizeY + 8 + offset);
    context.stroke();
  });
}

function drawCanvasSubtitlePill(
  context: CanvasRenderingContext2D,
  subtitle: string,
  x: number,
  y: number,
  maxRight: number,
  selected: boolean,
) {
  const availableWidth = Math.max(0, maxRight - x);
  if (availableWidth < 44) {
    return;
  }
  context.font = "850 12px Microsoft YaHei, sans-serif";
  const label = measureClampedCanvasText(context, subtitle, availableWidth - 18);
  const width = Math.min(availableWidth, context.measureText(label).width + 18);
  context.fillStyle = selected ? "rgba(47, 119, 189, 0.14)" : "rgba(47, 119, 189, 0.1)";
  roundRect(context, x, y, width, 24, 12);
  context.fill();
  context.fillStyle = selected ? "#225b87" : "#607186";
  context.fillText(label, x + 9, y + 16);
}

function measureClampedCanvasText(context: CanvasRenderingContext2D, text: string, maxWidth: number) {
  if (context.measureText(text).width <= maxWidth) {
    return text;
  }
  let nextText = text;
  while (nextText.length > 1 && context.measureText(`${nextText}...`).width > maxWidth) {
    nextText = nextText.slice(0, -1);
  }
  return `${nextText}...`;
}

function drawArrow(
  context: CanvasRenderingContext2D,
  from: MorphCanvasItem,
  to: MorphCanvasItem,
  state: { active: boolean; selected: boolean },
) {
  const geometry = calculateRelationArrowGeometry(from, to);
  const color = state.selected ? "#a66a1f" : state.active ? "#14536b" : "#28766f";
  context.strokeStyle = state.selected ? "#9a631d" : state.active ? "#14536b" : "#28766f";
  context.lineWidth = state.selected ? 8 : state.active ? 6 : 5;
  context.lineCap = "round";
  context.beginPath();
  context.moveTo(geometry.start.x, geometry.start.y);
  context.bezierCurveTo(
    geometry.controlStart.x,
    geometry.controlStart.y,
    geometry.controlEnd.x,
    geometry.controlEnd.y,
    geometry.shaftEnd.x,
    geometry.shaftEnd.y,
  );
  context.stroke();
  context.lineCap = "butt";
  context.fillStyle = color;
  context.beginPath();
  context.moveTo(geometry.tip.x, geometry.tip.y);
  context.lineTo(geometry.baseLeft.x, geometry.baseLeft.y);
  context.lineTo(geometry.baseRight.x, geometry.baseRight.y);
  context.closePath();
  context.fill();
}

function hitTest(items: MorphCanvasItem[], world: { x: number; y: number }) {
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const item = items[index];
    if (world.x >= item.x && world.x <= item.x + item.w && world.y >= item.y && world.y <= item.y + item.h) {
      return item;
    }
  }
  return null;
}

function hitTestNodeControl(items: MorphCanvasItem[], world: { x: number; y: number }): { item: MorphCanvasItem; mode: NodeDragMode } | null {
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const item = items[index];
    const resizeLeft = item.x + item.w - STAGE_NODE_RESIZE_HIT_SIZE;
    const resizeTop = item.y + item.h - STAGE_NODE_RESIZE_HIT_SIZE;
    const resizeRight = item.x + item.w + STAGE_NODE_CONTROL_OUTSET;
    const resizeBottom = item.y + item.h + STAGE_NODE_CONTROL_OUTSET;
    if (world.x >= resizeLeft && world.x <= resizeRight && world.y >= resizeTop && world.y <= resizeBottom) {
      return { item, mode: "resize" };
    }

    const inTitleBar =
      world.x >= item.x &&
      world.x <= item.x + item.w &&
      world.y >= item.y &&
      world.y <= item.y + Math.min(STAGE_NODE_TITLE_BAR_HEIGHT, item.h);
    const inTopRightGrip =
      world.x >= item.x + item.w - STAGE_NODE_CONTROL_OUTSET &&
      world.x <= item.x + item.w + STAGE_NODE_CONTROL_OUTSET &&
      world.y >= item.y - STAGE_NODE_CONTROL_OUTSET * 0.5 &&
      world.y <= item.y + STAGE_NODE_CONTROL_OUTSET;
    if (inTitleBar || inTopRightGrip) {
      return { item, mode: "move" };
    }
  }
  return null;
}

function hitTestRelation(
  items: MorphCanvasItem[],
  windows: DesignMorphWindowViewModel[],
  world: { x: number; y: number },
): DesignMorphWindowViewModel | null {
  for (let index = windows.length - 1; index >= 0; index -= 1) {
    const window = windows[index];
    const from = items.find((item) => item.id === window.fromStageId);
    const to = items.find((item) => item.id === window.toStageId);
    if (!from || !to) {
      continue;
    }
    const points = calculateRelationPolyline(from, to);
    for (let pointIndex = 0; pointIndex < points.length - 1; pointIndex += 1) {
      if (distanceToSegment(world, points[pointIndex], points[pointIndex + 1]) <= STAGE_RELATION_HIT_WIDTH) {
        return window;
      }
    }
    const labelCenter = points[Math.floor(points.length / 2)];
    if (
      world.x >= labelCenter.x - 44 &&
      world.x <= labelCenter.x + 44 &&
      world.y >= labelCenter.y - 26 &&
      world.y <= labelCenter.y + 12
    ) {
      return window;
    }
  }
  return null;
}

function calculateRelationPolyline(from: MorphCanvasItem, to: MorphCanvasItem) {
  const geometry = calculateRelationArrowGeometry(from, to);
  const points: Array<{ x: number; y: number }> = [];
  for (let index = 0; index <= 16; index += 1) {
    const t = index / 16;
    points.push(cubicBezierPoint(
      geometry.start,
      geometry.controlStart,
      geometry.controlEnd,
      geometry.shaftEnd,
      t,
    ));
  }
  return points;
}

export function calculateRelationArrowGeometry(from: RelationGeometryItem, to: RelationGeometryItem): RelationArrowGeometry {
  const start = {
    x: from.x + from.w + 28,
    y: from.y + from.h * 0.5,
  };
  const tip = {
    x: to.x - 28,
    y: to.y + to.h * 0.5,
  };
  const midX = from.x + from.w + (to.x - (from.x + from.w)) * 0.5;
  const baseDistance = 24;
  const baseHalfHeight = 12;
  const baseCenter = {
    x: tip.x - baseDistance,
    y: tip.y,
  };
  return {
    start,
    controlStart: { x: midX, y: start.y },
    controlEnd: { x: midX, y: tip.y },
    shaftEnd: baseCenter,
    tip,
    baseCenter,
    baseLeft: { x: baseCenter.x, y: baseCenter.y - baseHalfHeight },
    baseRight: { x: baseCenter.x, y: baseCenter.y + baseHalfHeight },
    labelCenter: {
      x: midX,
      y: (start.y + tip.y) / 2,
    },
  };
}

function cubicBezierPoint(
  p0: { x: number; y: number },
  p1: { x: number; y: number },
  p2: { x: number; y: number },
  p3: { x: number; y: number },
  t: number,
) {
  const oneMinusT = 1 - t;
  return {
    x: oneMinusT ** 3 * p0.x + 3 * oneMinusT ** 2 * t * p1.x + 3 * oneMinusT * t ** 2 * p2.x + t ** 3 * p3.x,
    y: oneMinusT ** 3 * p0.y + 3 * oneMinusT ** 2 * t * p1.y + 3 * oneMinusT * t ** 2 * p2.y + t ** 3 * p3.y,
  };
}

function distanceToSegment(point: { x: number; y: number }, start: { x: number; y: number }, end: { x: number; y: number }) {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const lengthSquared = dx * dx + dy * dy;
  if (lengthSquared === 0) {
    return Math.hypot(point.x - start.x, point.y - start.y);
  }
  const t = clamp(((point.x - start.x) * dx + (point.y - start.y) * dy) / lengthSquared, 0, 1);
  return Math.hypot(point.x - (start.x + t * dx), point.y - (start.y + t * dy));
}

function buildDocumentBlockSelection(
  item: MorphCanvasItem,
  block: StandardDocumentBlockViewModel,
  section: SelectableDocumentSection,
): DesignMorphSelection {
  const isRequirement = item.entityType === "requirement_specification";
  return {
    objectId: block.blockId,
    stageId: item.id,
    kind: isRequirement ? "requirement_clause" : "design_block",
    title: block.title ?? section.title,
    summary: block.content,
    status: section.status,
    sourceRefs: block.sourceRefs,
    qualityRefs: block.qualityRefs,
    actions: isRequirement
      ? [
          {
            actionId: "view_requirement_source",
            label: "查看来源",
            description: "定位 P2 冻结需规中的原始条款。",
          },
          {
            actionId: "locate_design_mapping",
            label: "定位软设映射",
            description: "查看该条款映射到哪些软设章节和结构化对象。",
          },
        ]
      : [
          {
            actionId: "expand_current_block",
            label: "扩写本段",
            description: "围绕当前软设段落补充设计理由、边界和接口说明。",
            commandHint: "扩写当前段落，补充模块边界和设计理由。",
          },
          {
            actionId: "append_subsection",
            label: "补充小节",
            description: "在当前章节下追加一个局部小节。",
          },
          {
            actionId: "apply_document_patch",
            label: "应用补丁",
            description: "把当前局部修改同步到正文和结构化事实。",
          },
        ],
    payload: {
      blockKind: block.kind,
      sectionId: section.section_id,
      sectionTitle: section.title,
      entityType: item.entityType,
    },
  };
}

function buildFunctionTreeNodeSelection(item: MorphCanvasItem, node: FunctionTreeNodeViewModel): DesignMorphSelection {
  const functionTree = item.functionTree;
  return {
    objectId: node.nodeId,
    stageId: item.id,
    kind: "function_node",
    title: node.title,
    summary: node.description,
    status: node.status,
    sourceRefs: node.sourceRefs,
    qualityRefs: [],
    actions: [
      {
        actionId: "view_function_node_requirement",
        label: "查看来源需规",
        description: "定位或展示该功能节点承接的 P2 需规条款。",
      },
      {
        actionId: "view_function_node_design_section",
        label: "查看软设章节",
        description: "定位或展示该功能节点对应的软件设计说明章节。",
      },
      {
        actionId: "filter_function_subtree",
        label: "只看当前子树",
        description: "在 Inspector 中以当前节点为根过滤树对象。",
      },
      {
        actionId: "filter_untraced_function_nodes",
        label: "只看未追溯",
        description: "筛选缺少来源或设计引用的功能节点。",
      },
      {
        actionId: "filter_pending_function_nodes",
        label: "只看待确认",
        description: "筛选待确认或待应用调整的功能节点。",
      },
      {
        actionId: "apply_function_tree_turn",
        label: "应用为设计轮次",
        description: "把当前功能树调整提交为可审计设计轮次。",
      },
    ],
    payload: {
      nodeId: node.nodeId,
      nodeType: node.nodeType,
      moduleId: node.moduleId,
      designRefs: node.designRefs,
      architectureRefs: node.architectureRefs,
      p4Refs: node.p4Refs,
      supportingNodes: collectFunctionTreeSupportingNodesForSelection(node),
      childCount: node.children.length,
      origin: functionTree?.origin ?? "empty",
      originLabel: getFunctionTreeOriginLabel(functionTree?.origin ?? "empty"),
      summary: functionTree?.summary ?? {
        nodeCount: 0,
        tracedNodeCount: 0,
        pendingNodeCount: 0,
        maxDepth: 0,
      },
      pendingAdjustmentSummary: "拖拽调整需提交为设计轮次后才会写入设计基线。",
    },
  };
}

function collectFunctionTreeSupportingNodesForSelection(node: FunctionTreeNodeViewModel): FunctionTreeNodeViewModel[] {
  return [
    ...(node.supportingNodes ?? []),
    ...node.children.flatMap((child) => collectFunctionTreeSupportingNodesForSelection(child)),
  ];
}

function getFunctionTreeOriginLabel(origin: FunctionTreeOrigin) {
  if (origin === "converter") {
    return "由转换器输出";
  }
  if (origin === "derived") {
    return "由当前设计基线派生";
  }
  return "等待生成功能树";
}

export function buildDesignMorphStageRelationSelection(window: DesignMorphWindowViewModel): DesignMorphSelection {
  const relation = getStageRelationDefinition(window);
  return {
    objectId: window.id,
    stageId: `${window.fromStageId}:${window.toStageId}`,
    kind: "stage_relation",
    title: window.title,
    summary: relation.summary,
    status: relation.status,
    sourceRefs: [window.fromStageId, window.toStageId],
    qualityRefs: [],
    actions: relation.actions,
    payload: {
      relationType: relation.relationType,
      label: relation.label,
      fromStageId: window.fromStageId,
      toStageId: window.toStageId,
      inputSummary: relation.inputSummary,
      outputSummary: relation.outputSummary,
    },
  };
}

function getStageRelationDefinition(window: DesignMorphWindowViewModel) {
  const definitions: Record<
    string,
    {
      relationType: string;
      label: string;
      status: string;
      summary: string;
      inputSummary: string;
      outputSummary: string;
      actions: DesignMorphSelectionAction[];
    }
  > = {
    reqdoc: {
      relationType: "requirement_to_design_document",
      label: "基础转换",
      status: "待执行",
      summary: "从 P2 冻结需规生成软件设计说明草稿，并建立正文、结构化事实和追溯映射。",
      inputSummary: "P2 冻结需求规格说明",
      outputSummary: "软件设计说明 A4 正文草稿",
      actions: [
        {
          actionId: "run_basic_conversion",
          label: "执行基础转换",
          description: "读取需规冻结包并生成软设草稿。",
        },
        {
          actionId: "view_relation_input",
          label: "查看输入",
          description: "定位当前转换关系使用的需规输入。",
        },
        {
          actionId: "view_relation_output",
          label: "查看输出",
          description: "定位基础转换生成的软设文档。",
        },
      ],
    },
    docfunc: {
      relationType: "design_document_to_function_tree",
      label: "功能拆解",
      status: "待生成",
      summary: "从软设章节拆解功能项和功能层级。",
      inputSummary: "软件设计说明正文",
      outputSummary: "功能树候选节点",
      actions: [{ actionId: "generate_function_tree", label: "生成功能树" }],
    },
    funcarch: {
      relationType: "function_tree_to_layered_architecture",
      label: "分层归属",
      status: "待生成",
      summary: "把功能节点归入展示层、功能层、服务层和数据层。",
      inputSummary: "功能树节点",
      outputSummary: "分层架构图",
      actions: [{ actionId: "generate_layered_architecture", label: "生成分层架构" }],
    },
    archtech: {
      relationType: "layered_architecture_to_technical_implementation",
      label: "技术映射",
      status: "待生成",
      summary: "把理论架构层映射到框架、模块、服务和数据对象。",
      inputSummary: "分层架构对象",
      outputSummary: "技术实现映射",
      actions: [{ actionId: "generate_technical_mapping", label: "生成技术映射" }],
    },
    techshape: {
      relationType: "technical_implementation_to_presentation_shape",
      label: "展示映射",
      status: "待生成",
      summary: "把技术模块映射到界面位置、组件形态和交互方式。",
      inputSummary: "技术实现模块",
      outputSummary: "展示形态候选",
      actions: [{ actionId: "generate_presentation_shape", label: "生成展示形态" }],
    },
    shapep4: {
      relationType: "presentation_shape_to_p4_projection",
      label: "投影候选",
      status: "待生成",
      summary: "从设计包派生 P4 工单和工具包树。",
      inputSummary: "展示形态和设计基线",
      outputSummary: "P4 工单投影树",
      actions: [{ actionId: "generate_projection_candidate", label: "生成投影候选" }],
    },
  };
  return (
    definitions[window.id] ?? {
      relationType: "custom_stage_relation",
      label: "阶段关系",
      status: "待处理",
      summary: `${window.fromStageId} 到 ${window.toStageId} 的阶段关系。`,
      inputSummary: window.fromStageId,
      outputSummary: window.toStageId,
      actions: [{ actionId: "inspect_relation", label: "查看关系" }],
    }
  );
}

function canvasPoint(canvas: HTMLCanvasElement, clientX: number, clientY: number) {
  const rect = canvas.getBoundingClientRect();
  return { x: clientX - rect.left, y: clientY - rect.top };
}

function screenToWorld(point: { x: number; y: number }, viewport: CanvasViewportState) {
  return { x: (point.x - viewport.x) / viewport.scale, y: (point.y - viewport.y) / viewport.scale };
}

function wrapCanvasText(
  context: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number,
  maxLines: number,
) {
  const chars = text.split("");
  let line = "";
  let lineCount = 0;
  for (const char of chars) {
    const testLine = `${line}${char}`;
    if (context.measureText(testLine).width > maxWidth && line) {
      context.fillText(line, x, y + lineCount * lineHeight);
      line = char;
      lineCount += 1;
      if (lineCount >= maxLines) {
        return;
      }
    } else {
      line = testLine;
    }
  }
  if (line && lineCount < maxLines) {
    context.fillText(line, x, y + lineCount * lineHeight);
  }
}

function roundRect(context: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number) {
  context.beginPath();
  context.moveTo(x + radius, y);
  context.arcTo(x + width, y, x + width, y + height, radius);
  context.arcTo(x + width, y + height, x, y + height, radius);
  context.arcTo(x, y + height, x, y, radius);
  context.arcTo(x, y, x + width, y, radius);
  context.closePath();
}
