import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";

import { ValidationWorkspace } from "../components/ValidationWorkspace";

test("renders a shared validation workspace shell with title, description, stats, and actions", () => {
  render(
    <ValidationWorkspace
      title="文档接入验证"
      description="用于查看导入状态、解析结果和异常信息。"
      actions={<button type="button">刷新</button>}
      stats={[
        { title: "文档总数", value: 67 },
        { title: "失败任务", value: 2 },
      ]}
    >
      <div>页面主体</div>
    </ValidationWorkspace>,
  );

  expect(screen.getByRole("heading", { name: "文档接入验证" })).toBeInTheDocument();
  expect(screen.getByText("用于查看导入状态、解析结果和异常信息。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "刷新" })).toBeInTheDocument();
  expect(screen.getByText("文档总数")).toBeInTheDocument();
  expect(screen.getByText("67")).toBeInTheDocument();
  expect(screen.getByText("失败任务")).toBeInTheDocument();
  expect(screen.getByText("2")).toBeInTheDocument();
  expect(screen.getByText("页面主体")).toBeInTheDocument();
});
