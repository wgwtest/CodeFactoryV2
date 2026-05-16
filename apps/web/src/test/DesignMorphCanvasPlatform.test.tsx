import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, test, vi } from "vitest";

import {
  DesignMorphCanvasPlatform,
  type DesignMorphStageViewModel,
  type DesignMorphWindowViewModel,
} from "../components/stageWorkbench/DesignMorphCanvasPlatform";

describe("DesignMorphCanvasPlatform", () => {
  test("keeps the user viewport when the parent refreshes data without changing the active window", () => {
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(buildCanvasContextMock());
    const getBoundingClientRect = vi.spyOn(HTMLCanvasElement.prototype, "getBoundingClientRect").mockReturnValue({
      x: 0,
      y: 0,
      width: 1000,
      height: 620,
      top: 0,
      right: 1000,
      bottom: 620,
      left: 0,
      toJSON: () => ({}),
    } as DOMRect);

    render(<CanvasRefreshHarness />);

    const platform = screen.getByTestId("design-morph-canvas-platform");
    const mainCanvas = within(platform).getByTestId("design-morph-main-canvas");
    expect(within(platform).getByText("缩放 90%")).toBeInTheDocument();

    fireEvent.wheel(mainCanvas, { deltaY: -600, clientX: 500, clientY: 310 });
    expect(within(platform).getByText("缩放 97%")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "模拟父级刷新" }));

    expect(within(platform).getByText("缩放 97%")).toBeInTheDocument();
    expect(within(platform).queryByText("缩放 90%")).not.toBeInTheDocument();

    getContext.mockRestore();
    getBoundingClientRect.mockRestore();
  });
});

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
    { id: "requirement", title: "需规", subtitle: "P2 冻结输入", summary: `需规 ${revision}`, items: ["需规正文"] },
    { id: "document", title: "软设文档", subtitle: "A4 正文形态", summary: `软设 ${revision}`, items: ["总体架构"] },
    { id: "functionTree", title: "功能树", subtitle: "从正文拆解功能项", summary: `功能树 ${revision}`, items: ["规划任务管理"] },
    { id: "layeredArchitecture", title: "分层架构", subtitle: "按层次放置设计对象", summary: `架构 ${revision}`, items: ["展示层"] },
    { id: "technicalImplementation", title: "技术实现", subtitle: "映射框架与真实模块", summary: `技术 ${revision}`, items: ["unified_service"] },
    { id: "presentationShape", title: "展示形态", subtitle: "表达 UI 呈现方式", summary: `展示 ${revision}`, items: ["Canvas 长卷"] },
    { id: "p4Projection", title: "P4 投影", subtitle: "下游工具包树", summary: `投影 ${revision}`, items: ["P4-WO"] },
  ];
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

function buildCanvasContextMock() {
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
    rect: vi.fn(),
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
  } as unknown as CanvasRenderingContext2D;
}
