import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, test, vi, type Mock } from "vitest";

import {
  calculateTrackLabelY,
  calculateTrackStageLandmarks,
  calculateTrackViewportFrame,
  DesignMorphCanvasPlatform,
  resolveTrackStageStyle,
  type DesignMorphStageViewModel,
  type DesignMorphWindowViewModel,
} from "../components/stageWorkbench/DesignMorphCanvasPlatform";

describe("DesignMorphCanvasPlatform", () => {
  test("projects the real canvas viewport as the primary track window", () => {
    const items = [
      { x: 80, y: 120, w: 500, h: 640 },
      { x: 720, y: 120, w: 520, h: 640 },
      { x: 1380, y: 140, w: 520, h: 520 },
      { x: 2080, y: 60, w: 1180, h: 820 },
      { x: 3460, y: 150, w: 560, h: 560 },
      { x: 4200, y: 120, w: 560, h: 600 },
      { x: 4920, y: 150, w: 560, h: 520 },
    ];

    const zoomedIn = calculateTrackViewportFrame({
      height: 88,
      items,
      left: 36,
      right: 964,
      viewport: { x: -314, y: -3, scale: 0.9 },
      width: 1000,
    });
    const zoomedOut = calculateTrackViewportFrame({
      height: 88,
      items,
      left: 36,
      right: 964,
      viewport: { x: 30, y: 120, scale: 0.44 },
      width: 1000,
    });

    expect(zoomedIn.y).toBeLessThanOrEqual(18);
    expect(zoomedIn.height).toBeGreaterThanOrEqual(48);
    expect(zoomedOut.width).toBeGreaterThan(zoomedIn.width);
  });

  test("projects stage landmark width from real canvas node width without flattening the x axis size", () => {
    const landmarks = calculateTrackStageLandmarks({
      items: [
        { id: "requirement", title: "需规", x: 80, w: 500 },
        { id: "document", title: "软设文档", x: 720, w: 520 },
        { id: "architecture", title: "分层架构", x: 2080, w: 1180 },
      ],
      left: 36,
      right: 964,
    });

    const requirement = landmarks.find((item) => item.id === "requirement");
    const document = landmarks.find((item) => item.id === "document");
    const architecture = landmarks.find((item) => item.id === "architecture");

    expect(requirement?.width).toBeGreaterThan(140);
    expect(document?.width).toBeGreaterThan(requirement?.width ?? 0);
    expect(architecture?.width).toBeGreaterThan((document?.width ?? 0) * 2);
  });

  test("keeps stage labels away from the bottom edge of the track window", () => {
    expect(calculateTrackLabelY(88, 42)).toBeLessThanOrEqual(70);
    expect(calculateTrackLabelY(88, 42)).toBeGreaterThan(58);
  });

  test("uses distinctive stage colors instead of flattening all landmarks into teal and gray", () => {
    const styles = buildStages(0).map((stage, index) => resolveTrackStageStyle(stage.id, index, 0));
    const activeStyles = buildStages(0).map((stage, index) => resolveTrackStageStyle(stage.id, index, index));
    const distinctFills = new Set(styles.map((style) => style.fill));

    expect(distinctFills.size).toBeGreaterThanOrEqual(5);
    expect(styles[3].fill).not.toBe("#FFFFFF");
    expect(styles[5].fill).not.toBe("#FFFFFF");
    expect(activeStyles[3].fill).toBe("#D59B32");
    expect(activeStyles[5].fill).toBe("#7567D8");
  });

  test("keeps the user viewport when the parent refreshes data without changing the active window", () => {
    const canvasMock = mockCanvasEnvironment();

    render(<CanvasRefreshHarness />);

    const platform = screen.getByTestId("design-morph-canvas-platform");
    const mainCanvas = within(platform).getByTestId("design-morph-main-canvas");
    expect(within(platform).getByText("缩放 90%")).toBeInTheDocument();

    fireEvent.wheel(mainCanvas, { deltaY: -600, clientX: 500, clientY: 310 });
    expect(within(platform).getByText("缩放 97%")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "模拟父级刷新" }));

    expect(within(platform).getByText("缩放 97%")).toBeInTheDocument();
    expect(within(platform).queryByText("缩放 90%")).not.toBeInTheDocument();

    canvasMock.restore();
  });

  test("zooms the main viewport symmetrically when the user wheels over the real track window", () => {
    const canvasMock = mockCanvasEnvironment();

    render(<CanvasRefreshHarness />);

    const platform = screen.getByTestId("design-morph-canvas-platform");
    const trackCanvas = within(platform).getByTestId("design-morph-track-canvas");
    expect(within(platform).getByText("缩放 90%")).toBeInTheDocument();

    fireEvent.wheel(trackCanvas, { deltaY: -600, clientX: 170, clientY: 30 });

    expect(within(platform).getByText("缩放 97%")).toBeInTheDocument();

    canvasMock.restore();
  });

  test("pans the main viewport when the user drags the real track window body", () => {
    const canvasMock = mockCanvasEnvironment();

    render(<CanvasRefreshHarness />);

    const platform = screen.getByTestId("design-morph-canvas-platform");
    const trackCanvas = within(platform).getByTestId("design-morph-track-canvas");
    const initialPan = within(platform).getByText(/^平移 /).textContent;

    fireEvent.mouseDown(trackCanvas, { button: 0, clientX: 170, clientY: 30 });
    fireEvent.mouseMove(trackCanvas, { clientX: 240, clientY: 30 });
    fireEvent.mouseUp(trackCanvas, { clientX: 240, clientY: 30 });

    expect(within(platform).getByText("缩放 90%")).toBeInTheDocument();
    expect(within(platform).getByText(/^平移 /).textContent).not.toBe(initialPan);

    canvasMock.restore();
  });

  test("resizes the main viewport when the user drags the real track window handles", () => {
    const canvasMock = mockCanvasEnvironment();

    render(<CanvasRefreshHarness />);

    const platform = screen.getByTestId("design-morph-canvas-platform");
    const trackCanvas = within(platform).getByTestId("design-morph-track-canvas");

    fireEvent.mouseDown(trackCanvas, { button: 0, clientX: 286, clientY: 30 });
    fireEvent.mouseMove(trackCanvas, { clientX: 336, clientY: 30 });
    fireEvent.mouseUp(trackCanvas, { clientX: 336, clientY: 30 });

    expect(within(platform).queryByText("缩放 90%")).not.toBeInTheDocument();
    expect(readZoomPercent(platform)).toBeLessThan(90);

    canvasMock.restore();
  });

  test("keeps stage landmarks passive when the user clicks the track outside the real window", () => {
    const canvasMock = mockCanvasEnvironment();
    const onActiveWindowChange = vi.fn();

    render(
      <DesignMorphCanvasPlatform
        activeWindowId="reqdoc"
        stages={buildStages(0)}
        windows={buildWindows()}
        onActiveWindowChange={onActiveWindowChange}
      />,
    );

    const platform = screen.getByTestId("design-morph-canvas-platform");
    const trackCanvas = within(platform).getByTestId("design-morph-track-canvas");

    fireEvent.pointerUp(trackCanvas, { pointerId: 9, clientX: 500, clientY: 42 });

    expect(onActiveWindowChange).not.toHaveBeenCalled();

    canvasMock.restore();
  });

  test("moves a stage node when the user drags its title bar instead of panning the whole canvas", () => {
    const canvasMock = mockCanvasEnvironment();

    render(<CanvasRefreshHarness />);

    const platform = screen.getByTestId("design-morph-canvas-platform");
    const mainCanvas = within(platform).getByTestId("design-morph-main-canvas");
    const initialPan = readPanLabel(platform);
    expect(within(platform).getByText("节点：软设文档 @720,120 · 520x640")).toBeInTheDocument();

    fireEvent.mouseDown(mainCanvas, { button: 0, clientX: 280, clientY: 140 });
    fireEvent.mouseMove(mainCanvas, { clientX: 340, clientY: 170 });
    fireEvent.mouseUp(mainCanvas, { clientX: 340, clientY: 170 });

    expect(readPanLabel(platform)).toBe(initialPan);
    expect(within(platform).getByText("节点：软设文档 @787,153 · 520x640")).toBeInTheDocument();

    canvasMock.restore();
  });

  test("resizes a stage node from its bottom-right handle and updates the track projection", () => {
    const canvasMock = mockCanvasEnvironment();

    render(<CanvasRefreshHarness />);

    const platform = screen.getByTestId("design-morph-canvas-platform");
    const mainCanvas = within(platform).getByTestId("design-morph-main-canvas");
    const trackCanvas = within(platform).getByTestId("design-morph-track-canvas");
    const initialTrackDraws = canvasMock.context.rect.mock.calls.length;

    expect(within(platform).getByText("节点：软设文档 @720,120 · 520x640")).toBeInTheDocument();

    fireEvent.mouseDown(mainCanvas, { button: 0, clientX: 780, clientY: 605 });
    fireEvent.mouseMove(mainCanvas, { clientX: 840, clientY: 655 });
    fireEvent.mouseUp(mainCanvas, { clientX: 840, clientY: 655 });
    fireEvent.wheel(trackCanvas, { deltaY: -600, clientX: 195, clientY: 30 });

    expect(within(platform).getByText("节点：软设文档 @720,120 · 587x696")).toBeInTheDocument();
    expect(canvasMock.context.rect.mock.calls.length).toBeGreaterThan(initialTrackDraws);

    canvasMock.restore();
  });
});

function readZoomPercent(platform: HTMLElement) {
  const label = within(platform).getByText(/^缩放 /).textContent ?? "";
  return Number(label.replace(/[^\d]/g, ""));
}

function readPanLabel(platform: HTMLElement) {
  return within(platform).getByText(/^平移 /).textContent;
}

function CanvasRefreshHarness() {
  const [revision, setRevision] = useState(0);
  const [activeWindowId, setActiveWindowId] = useState("reqdoc");
  const stages = buildStages(revision);
  const windows = buildWindows();

  return (
    <>
      <button type="button" onClick={() => setRevision((value) => value + 1)}>
        模拟父级刷新
      </button>
      <DesignMorphCanvasPlatform
        activeWindowId={activeWindowId}
        stages={stages}
        windows={windows}
        onActiveWindowChange={setActiveWindowId}
      />
    </>
  );
}

function buildStages(revision: number): DesignMorphStageViewModel[] {
  return [
    buildStage("requirement", "requirement_specification", "paper", "需规", "P2 冻结输入", `需规 ${revision}`, ["需规正文"]),
    buildStage("document", "software_design_document", "paper", "软设文档", "A4 正文形态", `软设 ${revision}`, ["总体架构"]),
    buildStage("functionTree", "software_function_tree", "tree", "功能树", "从正文拆解功能项", `功能树 ${revision}`, ["规划任务管理"]),
    buildStage("layeredArchitecture", "software_layered_architecture", "architecture", "分层架构", "按层次放置设计对象", `架构 ${revision}`, ["展示层"]),
    buildStage("technicalImplementation", "technical_implementation", "table", "技术实现", "映射框架与真实模块", `技术 ${revision}`, ["unified_service"]),
    buildStage("presentationShape", "presentation_shape", "cards", "展示形态", "表达 UI 呈现方式", `展示 ${revision}`, ["Canvas 长卷"]),
    buildStage("p4Projection", "module_workorder_projection", "tree", "P4 投影", "下游工具包树", `投影 ${revision}`, ["P4-WO"]),
  ];
}

function buildStage(
  id: DesignMorphStageViewModel["id"],
  entityType: DesignMorphStageViewModel["entityType"],
  layoutKind: DesignMorphStageViewModel["layoutKind"],
  title: string,
  subtitle: string,
  summary: string,
  items: string[],
): DesignMorphStageViewModel {
  return {
    id,
    entityType,
    layoutKind,
    title,
    subtitle,
    summary,
    items,
    sourceRefs: [`source:${id}`],
    constraintSummary: `约束 ${id}`,
  };
}

function buildWindows(): DesignMorphWindowViewModel[] {
  return [
    { id: "reqdoc", title: "需规 -> 软设文档", fromStageId: "requirement", toStageId: "document" },
    { id: "docfunc", title: "软设文档 -> 功能树", fromStageId: "document", toStageId: "functionTree" },
    { id: "funcarch", title: "功能树 -> 分层架构", fromStageId: "functionTree", toStageId: "layeredArchitecture" },
    { id: "archtech", title: "分层架构 -> 技术实现", fromStageId: "layeredArchitecture", toStageId: "technicalImplementation" },
    { id: "techshape", title: "技术实现 -> 展示形态", fromStageId: "technicalImplementation", toStageId: "presentationShape" },
    { id: "shapep4", title: "展示形态 -> P4 投影", fromStageId: "presentationShape", toStageId: "p4Projection" },
  ];
}

type CanvasContextMock = CanvasRenderingContext2D & {
  rect: Mock<(x: number, y: number, w: number, h: number) => void>;
};

function buildCanvasContextMock(): CanvasContextMock {
  return {
    arcTo: vi.fn(),
    beginPath: vi.fn(),
    bezierCurveTo: vi.fn(),
    clearRect: vi.fn(),
    closePath: vi.fn(),
    fill: vi.fn(),
    fillRect: vi.fn(),
    fillText: vi.fn(),
    getImageData: vi.fn(),
    lineTo: vi.fn(),
    measureText: vi.fn((text: string) => ({ width: text.length * 12 })),
    moveTo: vi.fn(),
    rect: vi.fn<(x: number, y: number, w: number, h: number) => void>(),
    restore: vi.fn(),
    save: vi.fn(),
    scale: vi.fn(),
    setTransform: vi.fn(),
    stroke: vi.fn(),
    strokeRect: vi.fn(),
    translate: vi.fn(),
    fillStyle: "",
    font: "",
    lineWidth: 1,
    strokeStyle: "",
    textAlign: "left",
  } as unknown as CanvasContextMock;
}

function mockCanvasEnvironment() {
  if (!HTMLCanvasElement.prototype.setPointerCapture) {
    HTMLCanvasElement.prototype.setPointerCapture = () => undefined;
  }
  const context = buildCanvasContextMock();
  const getContext = vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(context);
  const getBoundingClientRect = vi
    .spyOn(HTMLCanvasElement.prototype, "getBoundingClientRect")
    .mockImplementation(function getCanvasRect(this: HTMLCanvasElement) {
      const isTrack = this.className.toString().includes("track");
      const height = isTrack ? 88 : 620;
      return {
        x: 0,
        y: 0,
        width: 1000,
        height,
        top: 0,
        right: 1000,
        bottom: height,
        left: 0,
        toJSON: () => ({}),
      } as DOMRect;
    });
  const setPointerCapture = vi
    .spyOn(HTMLCanvasElement.prototype, "setPointerCapture")
    .mockImplementation(() => undefined);

  return {
    context,
    restore: () => {
      getContext.mockRestore();
      getBoundingClientRect.mockRestore();
      setPointerCapture.mockRestore();
    },
  };
}
