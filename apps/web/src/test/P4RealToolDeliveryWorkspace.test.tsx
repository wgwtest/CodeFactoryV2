import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { P4RealToolDeliveryWorkspace } from "../components/p4/P4RealToolDeliveryWorkspace";

const getMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
  },
}));

test("shows the real delivery workspace with peer dependency and import guidance", async () => {
  getMock.mockImplementation((url: string) => {
    if (url === "/tool-hub/tools/tool-query-table/delivery-manifest") {
      return Promise.resolve({
        data: {
          tool_id: "tool-query-table",
          tool_name: "查询表格元组件",
          tool_form_id: "frontend_component",
          packaging_type: "source_package",
          integration_mode: "import_component",
          dependency_policy: "peer",
          runtime_dependencies: ["react@18", "antd@5"],
          import_specifier: "@p4-tools/query-table-widget",
          example_host_path: "example/HostPage.tsx",
          artifact_version_id: "artifact-1",
          manifest_path: "/tmp/tool-query-table/manifest.json",
          contract_version: "p4.delivery.v1",
          updated_at: "2026-04-19T10:00:00Z",
        },
      });
    }
    throw new Error(`unexpected get url: ${url}`);
  });

  render(<P4RealToolDeliveryWorkspace initialToolId="tool-query-table" />);

  expect(await screen.findByText("真实工具交付")).toBeInTheDocument();
  expect(screen.getByText("peer")).toBeInTheDocument();
  expect(screen.getByText("@p4-tools/query-table-widget")).toBeInTheDocument();
  expect(screen.getByText("react@18")).toBeInTheDocument();
});
