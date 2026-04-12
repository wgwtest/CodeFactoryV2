import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { ValidationDrawer } from "../components/ValidationDrawer";

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

test("renders standard loading, error, and content states", () => {
  const onClose = vi.fn();
  const { rerender } = render(
    <ValidationDrawer
      title="实体详情"
      open
      onClose={onClose}
      loading
      loadingText="正在加载实体详情..."
      error={null}
      errorMessage="实体详情暂不可用"
    >
      <div>详情内容</div>
    </ValidationDrawer>,
  );

  expect(screen.getByText("正在加载实体详情...")).toBeInTheDocument();

  rerender(
    <ValidationDrawer
      title="实体详情"
      open
      onClose={onClose}
      loading={false}
      loadingText="正在加载实体详情..."
      error="服务异常"
      errorMessage="实体详情暂不可用"
    >
      <div>详情内容</div>
    </ValidationDrawer>,
  );

  expect(screen.getByText("实体详情暂不可用")).toBeInTheDocument();
  expect(screen.getByText("服务异常")).toBeInTheDocument();

  rerender(
    <ValidationDrawer
      title="实体详情"
      open
      onClose={onClose}
      loading={false}
      loadingText="正在加载实体详情..."
      error={null}
      errorMessage="实体详情暂不可用"
    >
      <div>详情内容</div>
    </ValidationDrawer>,
  );

  expect(screen.getByText("详情内容")).toBeInTheDocument();
});
