import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { ProcessViewPage } from "../pages/ProcessViewPage";

const getMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args)
  }
}));

test("renders archive processes", async () => {
  getMock.mockResolvedValue({
    data: [
      {
        id: "process-interoperability",
        name: "服务互操作流程",
        category: "domain_process",
        document_ids: ["doc-1"],
        evidence: [{ document_id: "doc-1", excerpt: "NAS远期需求文档的服务互操作性过程流" }]
      },
      {
        id: "process-roadmap",
        name: "服务演进路线图规划",
        category: "domain_process",
        document_ids: ["doc-2", "doc-3"],
        evidence: []
      }
    ]
  });

  render(
    <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <ProcessViewPage />
    </MemoryRouter>,
  );

  expect(await screen.findByText("服务互操作流程")).toBeInTheDocument();
  expect(await screen.findByText("服务演进路线图规划")).toBeInTheDocument();
  expect(await screen.findByText("1 份文档")).toBeInTheDocument();
  expect(await screen.findByText("2 份文档")).toBeInTheDocument();
});
