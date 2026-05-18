import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { A4DocumentSurface } from "../components/stageWorkbench/A4DocumentSurface";

describe("A4DocumentSurface", () => {
  test("renders long documents on a continuous paper sheet instead of a single fixed page", () => {
    render(
      <A4DocumentSurface
        ariaLabel="长文档 A4 预览"
        footerLeft="v0.1"
        footerRight="Page 1"
        headerLeft="CodeFactoryV2 / P3"
        headerRight="Software Design Description"
        sections={Array.from({ length: 12 }, (_, index) => ({
          section_id: `section-${index + 1}`,
          title: `${index + 1}. 长章节`,
          content: "这是一段用于撑开文档滚动高度的正文。".repeat(18),
          status: "generated",
        }))}
        subtitle="连续纸面验证"
        title="长软件设计说明"
      />,
    );

    expect(screen.getByLabelText("长文档 A4 预览")).toHaveClass("is-continuous-paper");
    expect(screen.getByTestId("a4-document-page")).toHaveClass("is-continuous-paper");
    expect(screen.getByTestId("a4-document-content")).toContainElement(screen.getByText("12. 长章节"));
  });

  test("can delegate scrolling to the canvas document object without creating a nested scroll surface", () => {
    render(
      <A4DocumentSurface
        ariaLabel="Canvas 需规文档预览"
        footerLeft="P2 Frozen Package"
        headerLeft="CodeFactoryV2 / P2"
        headerRight="Requirement Specification"
        scrollMode="parent"
        sections={[
          {
            section_id: "section-1",
            title: "1. 功能需求",
            content: "支持规划任务管理。".repeat(40),
            status: "generated",
          },
        ]}
        title="空域协同规划需求规格说明"
      />,
    );

    expect(screen.getByLabelText("Canvas 需规文档预览")).toHaveClass("is-parent-scroll");
    expect(screen.getByTestId("a4-document-page")).toHaveClass("is-continuous-paper");
  });
});
