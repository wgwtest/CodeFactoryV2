import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, test, vi, type Mock } from "vitest";

import {
  calculateRelationArrowGeometry,
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

  test("renders requirement and software design as compact executable document objects", () => {
    const canvasMock = mockCanvasEnvironment();

    render(
      <DesignMorphCanvasPlatform
        activeWindowId="reqdoc"
        stages={buildStages(0)}
        windows={buildWindows()}
        onActiveWindowChange={vi.fn()}
      />,
    );

    const platform = screen.getByTestId("design-morph-canvas-platform");
    const objectLayer = within(platform).getByTestId("design-morph-object-layer");
    const requirementObject = within(objectLayer).getByTestId("stage-object-requirement");
    const documentObject = within(objectLayer).getByTestId("stage-object-document");

    expect(requirementObject).toHaveClass("is-document-stage-object");
    expect(documentObject).toHaveClass("is-document-stage-object");
    expect(within(requirementObject).getByTestId("stage-object-compact-titlebar")).toBeInTheDocument();
    expect(within(documentObject).getByTestId("stage-object-compact-titlebar")).toBeInTheDocument();
    expect(within(requirementObject).getByRole("button", { name: "需规 A4" })).toHaveAttribute("aria-pressed", "true");
    expect(within(requirementObject).getByRole("button", { name: "需规 编辑区" })).toBeInTheDocument();
    expect(within(documentObject).getByRole("button", { name: "软设文档 A4" })).toHaveAttribute("aria-pressed", "true");
    expect(within(documentObject).getByRole("button", { name: "软设文档 编辑区" })).toBeInTheDocument();
    expect(within(requirementObject).getByTestId("document-stage-scroll")).toHaveClass("stage-document-scroll");
    expect(within(documentObject).getByTestId("document-stage-scroll")).toHaveClass("stage-document-scroll");
    expect(within(requirementObject).getByTestId("document-stage-paper")).toHaveTextContent("支持规划任务管理。");
    expect(within(documentObject).getByTestId("document-stage-paper")).toHaveTextContent("采用统一服务优先。");
    expect(within(objectLayer).queryByTestId("stage-object-functionTree")).not.toBeInTheDocument();

    canvasMock.restore();
  });

  test("reports a selected document block when the user clicks inside an A4 object", () => {
    const canvasMock = mockCanvasEnvironment();
    const onSelectMorphObject = vi.fn();

    render(
      <DesignMorphCanvasPlatform
        activeWindowId="reqdoc"
        stages={buildStages(0)}
        windows={buildWindows()}
        onActiveWindowChange={vi.fn()}
        onSelectMorphObject={onSelectMorphObject}
      />,
    );

    const platform = screen.getByTestId("design-morph-canvas-platform");
    const documentObject = within(platform).getByTestId("stage-object-document");

    fireEvent.click(within(documentObject).getByText("采用统一服务优先。"));

    expect(onSelectMorphObject).toHaveBeenCalledWith(
      expect.objectContaining({
        objectId: "sdd-1-body",
        stageId: "document",
        kind: "design_block",
        title: "总体架构",
        summary: "采用统一服务优先。",
        sourceRefs: ["REQ-1"],
      }),
    );

    canvasMock.restore();
  });

  test("selects a stage relation when the user clicks the arrow between two stage objects", () => {
    const canvasMock = mockCanvasEnvironment();
    const onSelectMorphObject = vi.fn();

    render(
      <DesignMorphCanvasPlatform
        activeWindowId="reqdoc"
        stages={buildStages(0)}
        windows={buildWindows()}
        onActiveWindowChange={vi.fn()}
        onSelectMorphObject={onSelectMorphObject}
      />,
    );

    const platform = screen.getByTestId("design-morph-canvas-platform");
    const mainCanvas = within(platform).getByTestId("design-morph-main-canvas");
    const initialPan = readPanLabel(platform);

    fireEvent.mouseDown(mainCanvas, { button: 0, clientX: 205, clientY: 310 });
    fireEvent.mouseUp(mainCanvas, { clientX: 205, clientY: 310 });

    expect(readPanLabel(platform)).toBe(initialPan);
    expect(onSelectMorphObject).toHaveBeenCalledWith(
      expect.objectContaining({
        objectId: "reqdoc",
        stageId: "requirement:document",
        kind: "stage_relation",
        title: "需规 -> 软设文档",
      }),
    );

    canvasMock.restore();
  });

  test("keeps relation clicks focused on the arrow without jumping to the destination stage", () => {
    const canvasMock = mockCanvasEnvironment();

    render(<CanvasRefreshHarness />);

    const platform = screen.getByTestId("design-morph-canvas-platform");
    const mainCanvas = within(platform).getByTestId("design-morph-main-canvas");
    const initialPan = readPanLabel(platform);

    fireEvent.mouseDown(mainCanvas, { button: 0, clientX: 800, clientY: 292 });
    fireEvent.mouseUp(mainCanvas, { clientX: 800, clientY: 292 });

    expect(readPanLabel(platform)).toBe(initialPan);
    expect(within(platform).getByText("选中关系：软设文档 -> 功能树")).toBeInTheDocument();
    expect(within(platform).queryByText("选中：功能树")).not.toBeInTheDocument();

    canvasMock.restore();
  });

  test("terminates the arrow shaft at the arrowhead base instead of the visual tip", () => {
    const geometry = calculateRelationArrowGeometry(
      { x: 80, y: 120, w: 500, h: 640 },
      { x: 720, y: 120, w: 520, h: 640 },
    );

    expect(geometry.shaftEnd.x).toBeLessThan(geometry.tip.x);
    expect(geometry.shaftEnd.x).toBe(geometry.baseCenter.x);
    expect(geometry.baseLeft.x).toBeLessThan(geometry.tip.x);
    expect(geometry.baseRight.x).toBeLessThan(geometry.tip.x);
  });

  test("does not paint relation labels over arrows on the main canvas", () => {
    const canvasMock = mockCanvasEnvironment();

    render(
      <DesignMorphCanvasPlatform
        activeWindowId="reqdoc"
        stages={buildStages(0)}
        windows={buildWindows()}
        onActiveWindowChange={vi.fn()}
      />,
    );

    const paintedText = canvasMock.context.fillText.mock.calls.map(([text]) => String(text));

    expect(paintedText).not.toContain("基础转换");
    expect(paintedText).not.toContain("功能拆解");

    canvasMock.restore();
  });

  test("moves a document object when the user drags its visible compact title bar", () => {
    const canvasMock = mockCanvasEnvironment();

    render(<CanvasRefreshHarness />);

    const platform = screen.getByTestId("design-morph-canvas-platform");
    const documentObject = within(platform).getByTestId("stage-object-document");
    const titlebar = within(documentObject).getByTestId("stage-object-compact-titlebar");
    const initialPan = readPanLabel(platform);

    expect(within(platform).getByText("节点：软设文档 @720,120 · 520x640")).toBeInTheDocument();

    fireEvent.pointerDown(titlebar, { pointerId: 23, clientX: 280, clientY: 140 });
    fireEvent.pointerMove(titlebar, { pointerId: 23, clientX: 340, clientY: 170 });
    fireEvent.pointerUp(titlebar, { pointerId: 23, clientX: 340, clientY: 170 });

    expect(readPanLabel(platform)).toBe(initialPan);
    expect(within(platform).getByText("节点：软设文档 @787,153 · 520x640")).toBeInTheDocument();

    canvasMock.restore();
  });

  test("keeps document object title actions clickable without starting a title-bar drag", () => {
    const canvasMock = mockCanvasEnvironment();

    render(<CanvasRefreshHarness />);

    const platform = screen.getByTestId("design-morph-canvas-platform");
    const documentObject = within(platform).getByTestId("stage-object-document");
    const editButton = within(documentObject).getByRole("button", { name: "软设文档 编辑区" });
    const initialPan = readPanLabel(platform);

    expect(within(platform).getByText("节点：软设文档 @720,120 · 520x640")).toBeInTheDocument();

    fireEvent.pointerDown(editButton, { pointerId: 24, clientX: 520, clientY: 140 });
    fireEvent.pointerMove(editButton, { pointerId: 24, clientX: 580, clientY: 170 });
    fireEvent.pointerUp(editButton, { pointerId: 24, clientX: 580, clientY: 170 });
    fireEvent.click(editButton);

    expect(readPanLabel(platform)).toBe(initialPan);
    expect(within(platform).getByText("节点：软设文档 @720,120 · 520x640")).toBeInTheDocument();
    expect(editButton).toHaveAttribute("aria-pressed", "true");
    expect(within(documentObject).getByTestId("document-stage-paper")).toHaveClass("is-edit-mode");

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
    buildStage("requirement", "requirement_specification", "paper", "需规", "P2 冻结输入", `需规 ${revision}`, ["需规正文"], {
      title: "空域协同规划需求规格说明",
      subtitle: "P2 冻结输入 / 只读消费",
      headerLeft: "CodeFactoryV2 / P2",
      headerRight: "Requirement Specification",
      footerLeft: "P2 Frozen Package",
      footerRight: "Page 1",
      ariaLabel: "需规 A4 预览",
      emptyDescription: "没有可用的 P2 冻结包",
      structuredSections: [
        {
          sectionId: "req-1",
          title: "功能需求",
          status: "generated",
          blocks: [
            { blockId: "REQ-1", kind: "clause", title: "规划任务", content: "支持规划任务管理。", sourceRefs: ["REQ-1"], qualityRefs: [] },
          ],
        },
      ],
      sections: [
        { sectionId: "REQ-1", title: "规划任务", content: "支持规划任务管理。", status: "generated" },
      ],
    }),
    buildStage("document", "software_design_document", "paper", "软设文档", "A4 正文形态", `软设 ${revision}`, ["总体架构"], {
      title: "空域协同规划软件设计说明",
      subtitle: "基于 P2 需求规格冻结包生成",
      headerLeft: "CodeFactoryV2 / P3",
      headerRight: "Software Design Description",
      footerLeft: "v0.1",
      footerRight: "Page 1",
      ariaLabel: "软设文档 A4 预览",
      emptyDescription: "尚未生成软件设计说明",
      structuredSections: [
        {
          sectionId: "sdd-1",
          title: "总体架构",
          status: "generated",
          blocks: [
            { blockId: "sdd-1-body", kind: "paragraph", content: "采用统一服务优先。", sourceRefs: ["REQ-1"], qualityRefs: [] },
          ],
        },
      ],
      sections: [
        { sectionId: "sdd-1", title: "总体架构", content: "采用统一服务优先。", status: "generated" },
      ],
    }),
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
  document?: Partial<DesignMorphStageViewModel["document"]>,
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
    viewModes: document ? [{ id: "a4", label: "A4" }, { id: "edit", label: "编辑区" }] : undefined,
    document: document
      ? {
          title: document.title ?? title,
          subtitle: document.subtitle,
          headerLeft: document.headerLeft ?? "",
          headerRight: document.headerRight ?? "",
          footerLeft: document.footerLeft ?? "",
          footerRight: document.footerRight,
          ariaLabel: document.ariaLabel ?? `${title} A4`,
          emptyDescription: document.emptyDescription ?? "尚未生成文档",
          structuredSections: document.structuredSections,
          sections: document.sections ?? [],
        }
      : undefined,
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
  fillText: Mock<(text: string, x: number, y: number, maxWidth?: number) => void>;
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
  const previousPointerEvent = window.PointerEvent;
  if (!window.PointerEvent) {
    window.PointerEvent = MouseEvent as unknown as typeof PointerEvent;
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
      window.PointerEvent = previousPointerEvent;
    },
  };
}
