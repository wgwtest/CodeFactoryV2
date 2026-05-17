import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent as ReactWheelEvent,
} from "react";
import "./design-morph-canvas.css";

export type DesignMorphStageViewModel = {
  id: string;
  title: string;
  subtitle: string;
  summary: string;
  items: string[];
};

export type DesignMorphWindowViewModel = {
  id: string;
  title: string;
  fromStageId: string;
  toStageId: string;
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
  type: "paper" | "tree" | "architecture" | "table" | "cards";
  x: number;
  y: number;
  w: number;
  h: number;
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

type DesignMorphCanvasPlatformProps = {
  stages: DesignMorphStageViewModel[];
  windows: DesignMorphWindowViewModel[];
  activeWindowId: string;
  onActiveWindowChange: (windowId: string) => void;
};

const MIN_CANVAS_SCALE = 0.42;
const MAX_CANVAS_SCALE = 1.65;
const MIN_STAGE_NODE_WIDTH = 360;
const MIN_STAGE_NODE_HEIGHT = 360;
const STAGE_NODE_TITLE_BAR_HEIGHT = 168;
const STAGE_NODE_RESIZE_HIT_SIZE = 40;
const STAGE_NODE_CONTROL_OUTSET = 72;
const TRACK_PADDING_X = 36;
const TRACK_HANDLE_HIT_WIDTH = 16;
const INITIAL_VIEWPORT: CanvasViewportState = { x: -314, y: -3, scale: 0.9 };
const STAGE_LAYOUTS = [
  { x: 80, y: 120, w: 500, h: 640, type: "paper" },
  { x: 720, y: 120, w: 520, h: 640, type: "paper" },
  { x: 1380, y: 140, w: 520, h: 520, type: "tree" },
  { x: 2080, y: 60, w: 1180, h: 820, type: "architecture" },
  { x: 3460, y: 150, w: 560, h: 560, type: "table" },
  { x: 4200, y: 120, w: 560, h: 600, type: "cards" },
  { x: 4920, y: 150, w: 560, h: 520, type: "tree" },
] as const;

export function DesignMorphCanvasPlatform({
  stages,
  windows,
  activeWindowId,
  onActiveWindowChange,
}: DesignMorphCanvasPlatformProps) {
  const trackCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const mainCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const nodeDragRef = useRef<NodeDragState | null>(null);
  const trackDragRef = useRef<TrackDragState | null>(null);
  const itemsRef = useRef<MorphCanvasItem[]>([]);
  const lastAutoCenteredWindowKeyRef = useRef<string | null>(null);
  const [viewport, setViewport] = useState<CanvasViewportState>(INITIAL_VIEWPORT);
  const [selectedStageId, setSelectedStageId] = useState(stages[1]?.id ?? stages[0]?.id ?? "");
  const [layoutRevision, setLayoutRevision] = useState(0);
  const [stageLayouts, setStageLayouts] = useState<Record<string, CanvasStageLayoutState>>(() => buildCanvasLayoutState(stages));
  const items = useMemo(() => buildCanvasItems(stages, stageLayouts), [stageLayouts, stages]);
  const activePairIndex = Math.max(0, windows.findIndex((window) => window.id === activeWindowId));
  const activeWindow = windows[activePairIndex] ?? windows[0];
  const activeWindowKey = activeWindow ? `${activeWindow.id}:${activeWindow.toStageId}:${activePairIndex}` : "none";
  const selectedItem = items.find((item) => item.id === selectedStageId) ?? items[1] ?? items[0];

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  useEffect(() => {
    setStageLayouts((current) => reconcileCanvasLayouts(stages, current));
  }, [stages]);

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
    renderMainCanvas(mainCanvas, mainContext, items, selectedStageId, viewport);
    const mainRect = mainCanvas.getBoundingClientRect();
    renderTrackCanvas(trackCanvas, trackContext, items, activePairIndex, viewport, mainRect.width || 1190);
  }, [activePairIndex, items, layoutRevision, selectedStageId, viewport]);

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
    beginMainDrag(event.currentTarget, event.clientX, event.clientY, event.pointerId, "pointer");
    if (typeof event.currentTarget.setPointerCapture === "function") {
      event.currentTarget.setPointerCapture(event.pointerId);
    }
  }

  function handleMainMouseDown(event: ReactMouseEvent<HTMLCanvasElement>) {
    if (event.button !== 0 || dragRef.current || nodeDragRef.current) {
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
    const hit = hitTest(itemsRef.current, screenToWorld(point, viewport));
    if (hit) {
      setSelectedStageId(hit.id);
    }
  }

  function handleMainPointerLeave(event: ReactPointerEvent<HTMLCanvasElement>) {
    handleMainPointerUp(event);
    if (!dragRef.current && !nodeDragRef.current) {
      event.currentTarget.style.cursor = "grab";
    }
  }

  function handleMainMouseLeave(event: ReactMouseEvent<HTMLCanvasElement>) {
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
    const hit = hitTestNodeControl(itemsRef.current, screenToWorld(point, viewport));
    canvas.style.cursor = hit?.mode === "resize" ? "nwse-resize" : hit ? "move" : "grab";
  }

  function handleWheel(event: ReactWheelEvent<HTMLCanvasElement>) {
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
      onActiveWindowChange(nextWindow.id);
    }
  }

  function fitViewport() {
    setViewport({ scale: 0.44, x: 30, y: 120 });
  }

  function centerLargeArchitecture() {
    centerItem(stages[3]?.id ?? items[3]?.id ?? selectedStageId, 0.62);
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
        <div className="design-morph-hud">
          <span>Canvas 窗口：{activeWindow?.title ?? "需规 -> 软设文档"}</span>
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
        <span>{selectedStageId ? `选中：${items.find((item) => item.id === selectedStageId)?.title ?? selectedStageId}` : "选中：-"}</span>
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
        </div>
      </footer>
    </div>
  );
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
    type: "cards" as const,
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
      type: "cards" as const,
    };
    return {
      ...stage,
      index,
      type: layout.type,
      x: stageLayouts[stage.id]?.x ?? layout.x,
      y: stageLayouts[stage.id]?.y ?? layout.y,
      w: stageLayouts[stage.id]?.w ?? layout.w,
      h: stageLayouts[stage.id]?.h ?? layout.h,
    };
  });
}

function renderMainCanvas(
  canvas: HTMLCanvasElement,
  context: CanvasRenderingContext2D,
  items: MorphCanvasItem[],
  selectedStageId: string,
  viewport: CanvasViewportState,
) {
  const { width, height } = prepareCanvas(canvas, context, 1190, 788);
  context.clearRect(0, 0, width, height);
  drawCanvasBackground(context, width, height);
  context.save();
  context.translate(viewport.x, viewport.y);
  context.scale(viewport.scale, viewport.scale);
  for (let index = 0; index < items.length - 1; index += 1) {
    drawArrow(context, items[index], items[index + 1]);
  }
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
    const active = index === activePairIndex || index === activePairIndex + 1;
    context.fillStyle = active ? "#143e52" : index < activePairIndex ? "#e4f2e9" : "#fff";
    context.strokeStyle = active ? "#143e52" : index < activePairIndex ? "#80b995" : "#aebfba";
    context.lineWidth = 2;
    context.beginPath();
    context.rect(landmark.x, y - 8, landmark.width, 16);
    context.fill();
    context.stroke();
    context.fillStyle = active ? "rgba(255, 255, 255, 0.92)" : "#6f807d";
    context.fillRect(landmark.center - 1, y - 4, 2, 8);
    context.fillStyle = index < activePairIndex ? "#2b7448" : "#14211f";
    context.font = "900 12px Microsoft YaHei, sans-serif";
    context.textAlign = "center";
    context.fillText(item.title, landmark.center, y + 34);
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
  context.fillStyle = item.type === "architecture" ? "#fbfcfb" : "#fffdf8";
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

  context.fillStyle = selected ? "#143e52" : "#60706c";
  context.font = "850 15px Microsoft YaHei, sans-serif";
  context.fillText(item.subtitle, item.x + 24, item.y + 34);
  context.fillStyle = "#172221";
  context.font = "950 25px Microsoft YaHei, sans-serif";
  wrapCanvasText(context, item.title, item.x + 24, item.y + 74, item.w - 48, 30, 2);
  context.fillStyle = "#40514d";
  context.font = "14px Microsoft YaHei, sans-serif";
  wrapCanvasText(context, item.summary, item.x + 24, item.y + 132, item.w - 48, 23, 4);

  drawItemControls(context, item, selected);

  if (item.type === "architecture") {
    drawArchitectureItem(context, item);
    return;
  }
  if (item.type === "tree") {
    drawTreeItem(context, item);
    return;
  }
  if (item.type === "table") {
    drawTableItem(context, item);
    return;
  }
  if (item.type === "cards") {
    drawCardsItem(context, item);
    return;
  }
  drawPaperItem(context, item);
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

function drawPaperItem(context: CanvasRenderingContext2D, item: MorphCanvasItem) {
  const top = item.y + 234;
  context.fillStyle = "#f7faf9";
  roundRect(context, item.x + 28, top - 28, item.w - 56, item.h - 270, 6);
  context.fill();
  item.items.slice(0, 6).forEach((line, index) => {
    const y = top + index * 54;
    context.fillStyle = "#14211f";
    context.font = "850 14px Microsoft YaHei, sans-serif";
    context.fillText(`${index + 1}. ${line}`, item.x + 48, y);
    context.strokeStyle = "#d9e3df";
    context.lineWidth = 1;
    context.beginPath();
    context.moveTo(item.x + 48, y + 16);
    context.lineTo(item.x + item.w - 48, y + 16);
    context.stroke();
  });
}

function drawTreeItem(context: CanvasRenderingContext2D, item: MorphCanvasItem) {
  const startX = item.x + 52;
  const startY = item.y + 220;
  context.strokeStyle = "#9ab7ae";
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(startX, startY - 22);
  context.lineTo(startX, startY + Math.min(4, item.items.length - 1) * 58);
  context.stroke();
  item.items.slice(0, 5).forEach((line, index) => {
    const y = startY + index * 58;
    context.strokeStyle = "#9ab7ae";
    context.beginPath();
    context.moveTo(startX, y);
    context.lineTo(startX + 34, y);
    context.stroke();
    context.fillStyle = index === 0 ? "#e6f0f4" : "#f6faf8";
    roundRect(context, startX + 34, y - 20, item.w - 104, 40, 6);
    context.fill();
    context.strokeStyle = "#cbd9d4";
    context.stroke();
    context.fillStyle = "#172221";
    context.font = "850 14px Microsoft YaHei, sans-serif";
    context.fillText(line, startX + 50, y + 5);
  });
}

function drawArchitectureItem(context: CanvasRenderingContext2D, item: MorphCanvasItem) {
  const labels = item.items.length ? item.items : ["展示层", "功能层", "服务层", "数据层"];
  const top = item.y + 220;
  const layerHeight = 118;
  labels.slice(0, 5).forEach((label, index) => {
    const y = top + index * (layerHeight + 18);
    context.fillStyle = ["#e6f0f4", "#e4f2e9", "#f5e9d6", "#edf2f0", "#f8fbfa"][index] ?? "#f8fbfa";
    roundRect(context, item.x + 34, y, item.w - 68, layerHeight, 8);
    context.fill();
    context.strokeStyle = "#cad8d3";
    context.stroke();
    context.fillStyle = "#143e52";
    context.font = "950 16px Microsoft YaHei, sans-serif";
    context.fillText(label, item.x + 58, y + 32);
    context.fillStyle = "#40514d";
    context.font = "13px Microsoft YaHei, sans-serif";
    wrapCanvasText(context, `模块边界、服务职责、数据依赖和下游投影在本层形成可追溯设计对象。`, item.x + 58, y + 62, item.w - 116, 22, 2);
  });
}

function drawTableItem(context: CanvasRenderingContext2D, item: MorphCanvasItem) {
  const top = item.y + 218;
  item.items.slice(0, 6).forEach((line, index) => {
    const y = top + index * 54;
    context.fillStyle = index % 2 === 0 ? "#f7faf9" : "#fffdf8";
    context.fillRect(item.x + 28, y, item.w - 56, 48);
    context.strokeStyle = "#d7e0dc";
    context.strokeRect(item.x + 28, y, item.w - 56, 48);
    context.fillStyle = "#172221";
    context.font = "850 14px Microsoft YaHei, sans-serif";
    context.fillText(line, item.x + 48, y + 30);
  });
}

function drawCardsItem(context: CanvasRenderingContext2D, item: MorphCanvasItem) {
  const top = item.y + 216;
  const cardWidth = (item.w - 78) / 2;
  item.items.slice(0, 6).forEach((line, index) => {
    const x = item.x + 28 + (index % 2) * (cardWidth + 22);
    const y = top + Math.floor(index / 2) * 106;
    context.fillStyle = "#f8fbfa";
    roundRect(context, x, y, cardWidth, 82, 8);
    context.fill();
    context.strokeStyle = "#d7e0dc";
    context.stroke();
    context.fillStyle = "#172221";
    context.font = "850 14px Microsoft YaHei, sans-serif";
    wrapCanvasText(context, line, x + 16, y + 30, cardWidth - 32, 22, 2);
  });
}

function drawArrow(context: CanvasRenderingContext2D, from: MorphCanvasItem, to: MorphCanvasItem) {
  const startX = from.x + from.w;
  const startY = from.y + from.h * 0.5;
  const endX = to.x;
  const endY = to.y + to.h * 0.5;
  const midX = startX + (endX - startX) * 0.5;
  context.strokeStyle = "#28766f";
  context.lineWidth = 3;
  context.beginPath();
  context.moveTo(startX + 28, startY);
  context.bezierCurveTo(midX, startY, midX, endY, endX - 28, endY);
  context.stroke();
  context.fillStyle = "#28766f";
  context.beginPath();
  context.moveTo(endX - 28, endY);
  context.lineTo(endX - 46, endY - 9);
  context.lineTo(endX - 46, endY + 9);
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
