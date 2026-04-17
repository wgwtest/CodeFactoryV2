import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, vi } from "vitest";

import App from "../App";

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

function createRequirementSpec(
  id: string,
  applicationName: string,
  status = "ready",
  domainName = "国家空域管理",
) {
  return {
    id,
    application_name: applicationName,
    domain_name: domainName,
    status,
    archive_id: "20161116-nas",
    object_count: 5,
    formal_object_count: 4,
    temporary_object_count: 1,
    process_count: 2,
    updated_at: "2026-04-17T10:00:00Z",
  };
}

function mockP3WorkspaceState(options?: {
  initialOrder?: boolean;
  initialStatus?: string;
  specs?: Array<ReturnType<typeof createRequirementSpec>>;
}) {
  let orderId = "p3-order-1";
  let orderStatus = options?.initialOrder === false ? null : (options?.initialStatus ?? "pending_approval");
  let orderRequirementSpecId = orderStatus ? "spec-1" : null;
  let orderApplicationName = "空域协同规划软件";
  let orderDomainName = "国家空域管理";
  let designSections: Array<{ id: string; title: string; summary: string }> | null =
    orderStatus === "draft_ready" || orderStatus === "in_revision" || orderStatus === "frozen"
      ? [{ id: "goal", title: "1. 设计目标与范围", summary: "..." }]
      : null;
  let workorderBatch:
    | {
        package_overview: {
          architecture_recommendation: string;
          interaction_mode: string;
        };
        items: Array<{ item_id: string; title: string }>;
        push_status?: string;
      }
    | null = null;
  const specs = options?.specs ?? [createRequirementSpec("spec-1", "空域协同规划软件")];

  getMock.mockImplementation((url: string, config?: { params?: Record<string, string> }) => {
    if (url === "/software-design/overview") {
      return Promise.resolve({
        data: {
          data: {
            metrics: {
              order_count: orderStatus ? 1 : 0,
              pending_approval_count: orderStatus === "pending_approval" ? 1 : 0,
              frozen_count: orderStatus === "frozen" ? 1 : 0,
              package_ready_count: orderStatus === "package_ready" ? 1 : 0,
              pushed_count: orderStatus === "pushed_to_p4" ? 1 : 0,
            },
            recent_orders: [],
            recent_packages: [],
          },
        },
      });
    }

    if (url === "/requirements/specs") {
      return Promise.resolve({ data: specs });
    }

    if (url === "/software-design/orders") {
      return Promise.resolve({
        data: {
          data: {
            items: orderStatus
              ? [
                  {
                    order_id: orderId,
                    application_name: orderApplicationName,
                    requirement_spec_id: orderRequirementSpecId,
                    status: orderStatus,
                    updated_at: "2026-04-17T10:00:00Z",
                  },
                ]
              : [],
          },
        },
      });
    }

    if (url === "/software-design/reference-center") {
      return Promise.resolve({
        data: {
          templates: [
            {
              template_id: "template-sdd-82284",
              title: "DI-IPSC-82284A Software/Hardware Design Description",
              source_doc_id: "DI-IPSC-82284",
              document_type: "software_design_description",
              version: "A",
              format: "pdf",
              summary: "平台级软件工厂优先使用的软件设计说明模板骨架。",
              recommendation: "适合平台级软件设计说明。",
              official_detail_url: "https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=283200",
              pdf_asset_name: "template-sdd-82284.pdf",
              pdf_url: null,
              sections: [
                {
                  section_id: "scope",
                  title: "Architecture Overview",
                  summary: "说明平台级软件的总体架构、设计范围与关键约束。",
                },
                {
                  section_id: "interfaces",
                  title: "Interface Design",
                  summary: "描述模块边界、接口契约与数据交换要求。",
                },
                {
                  section_id: "traceability",
                  title: "Requirements Traceability",
                  summary: "将需求规格与后续模块工单建立追溯关系。",
                },
              ],
            },
          ],
          standards: [
            {
              doc_id: "DI-IPSC-82284",
              title: "Software/Hardware Design Description",
              category: "dod-did",
              scope: "platform_or_system",
              summary: "用于软件/硬件设计说明编制的军标数据项描述。",
              official_detail_url: "https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=283200",
              recommended_use: "用于平台级设计说明。",
              tags: ["design"],
              sections: [
                {
                  section_id: "std-scope",
                  title: "Scope",
                  summary: "Prescribes content for software design descriptions.",
                },
              ],
            },
          ],
          mappings: [
            {
              template_id: "template-sdd-82284",
              doc_id: "DI-IPSC-82284",
              rationale: "用于把 P3 软设章节与军标章节建立对应关系。",
              section_pairs: [
                {
                  template_section: "Architecture Overview",
                  standard_section: "Scope",
                },
                {
                  template_section: "Requirements Traceability",
                  standard_section: "Traceability",
                },
              ],
            },
          ],
        },
      });
    }

    if (url === "/software-design/standards/search") {
      return Promise.resolve({
        data: {
          items: [
            {
              doc_id: "DI-IPSC-82284",
              title: "Software/Hardware Design Description",
              matched_section: "Scope",
              excerpt: "Prescribes content for software and hardware design descriptions.",
            },
          ],
        },
      });
    }

    if (url === `/software-design/orders/${orderId}`) {
      return Promise.resolve({
        data: {
          order_id: orderId,
          requirement_spec_summary: {
            application_name: orderApplicationName,
            domain_name: orderDomainName,
            status: "ready",
          },
          status: orderStatus,
          design_description: designSections ? { sections: designSections } : null,
          review_threads: [],
          workorder_batch: workorderBatch,
        },
      });
    }

    throw new Error(`unexpected get url: ${url} ${JSON.stringify(config?.params ?? {})}`);
  });

  postMock.mockImplementation((url: string, payload?: { requirement_spec_id?: string }) => {
    if (url === "/software-design/orders") {
      const createdSpec = specs.find((spec) => spec.id === payload?.requirement_spec_id) ?? specs[0];
      orderId = "p3-order-created";
      orderStatus = "pending_approval";
      orderRequirementSpecId = createdSpec.id;
      orderApplicationName = createdSpec.application_name;
      orderDomainName = createdSpec.domain_name;
      designSections = null;
      workorderBatch = null;
      return Promise.resolve({ data: { order_id: orderId, status: orderStatus } });
    }

    if (url.endsWith("/approve")) {
      orderStatus = "approved_for_generation";
      return Promise.resolve({ data: { status: orderStatus } });
    }

    if (url.endsWith("/reject")) {
      orderStatus = "rejected";
      return Promise.resolve({ data: { status: orderStatus } });
    }

    if (url.endsWith("/generate-draft")) {
      orderStatus = "draft_ready";
      designSections = [{ id: "goal", title: "1. 设计目标与范围", summary: "..." }];
      return Promise.resolve({
        data: {
          status: orderStatus,
          design_description: {
            sections: designSections,
          },
        },
      });
    }

    if (url.endsWith("/freeze")) {
      orderStatus = "frozen";
      return Promise.resolve({ data: { status: orderStatus } });
    }

    if (url.endsWith("/workorder-batch")) {
      orderStatus = "package_ready";
      workorderBatch = {
        package_overview: {
          architecture_recommendation: "unified_service",
          interaction_mode: "bs",
        },
        items: [{ item_id: "item-1", title: "规划任务管理模块实现" }],
      };
      return Promise.resolve({ data: workorderBatch });
    }

    if (url.endsWith("/push-to-p4")) {
      orderStatus = "pushed_to_p4";
      workorderBatch = workorderBatch
        ? {
            ...workorderBatch,
            push_status: "pushed",
          }
        : workorderBatch;
      return Promise.resolve({ data: { push_status: "pushed" } });
    }

    throw new Error(`unexpected post url: ${url}`);
  });
}

test("renders XX-P3 cockpit route and refreshes order status through the workflow", async () => {
  mockP3WorkspaceState();

  render(
    <MemoryRouter initialEntries={["/xx-p3"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("XX-P3")).toBeInTheDocument();
  expect(screen.getByText("软件设计编制与模块工单下发系统")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "审批通过" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "接收为P3订单" })).toBeDisabled();

  fireEvent.click(screen.getByRole("button", { name: "审批通过" }));
  await waitFor(() => expect(screen.getAllByText("approved_for_generation").length).toBeGreaterThan(0));

  fireEvent.click(screen.getByRole("button", { name: "生成软设草案" }));
  await waitFor(() => expect(screen.getAllByText("draft_ready").length).toBeGreaterThan(0));

  fireEvent.click(screen.getByRole("tab", { name: "设计编制" }));
  expect(await screen.findByText("1. 设计目标与范围")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: "模块工单包" }));
  fireEvent.click(screen.getByRole("button", { name: "生成批次工单包" }));
  expect(await screen.findByText("规划任务管理模块实现")).toBeInTheDocument();
  expect(screen.getByText("unified_service")).toBeInTheDocument();
  await waitFor(() => expect(screen.getAllByText("package_ready").length).toBeGreaterThan(0));

  fireEvent.click(screen.getByRole("button", { name: "推送到 P4" }));
  await waitFor(() => expect(postMock).toHaveBeenCalledWith("/software-design/orders/p3-order-1/push-to-p4"));
  await waitFor(() => expect(screen.getAllByText("pushed_to_p4").length).toBeGreaterThan(0));
});

test("renders template and standards workspace when there are no orders", async () => {
  mockP3WorkspaceState({ initialOrder: false });

  render(
    <MemoryRouter initialEntries={["/xx-p3"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("tab", { name: "模板与规范" })).toBeInTheDocument();
  expect(screen.getByText("当前没有订单")).toBeInTheDocument();
  expect(screen.getByText("模板清单")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /细\s*节/ })).toBeInTheDocument();
  expect(screen.queryByText("打开源 PDF")).not.toBeInTheDocument();
  expect(screen.queryByText("模板骨架解析")).not.toBeInTheDocument();
  expect(screen.queryByTitle("模板 PDF 阅读器")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "检索规范" }));

  expect((await screen.findAllByText("DI-IPSC-82284A Software/Hardware Design Description")).length).toBeGreaterThan(0);
  expect(screen.getByText("Software/Hardware Design Description")).toBeInTheDocument();
});

test("opens template details on a dedicated page from the compact P3 workspace", async () => {
  mockP3WorkspaceState({ initialOrder: false });

  render(
    <MemoryRouter initialEntries={["/xx-p3"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("模板清单")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /细\s*节/ }));

  expect(await screen.findByText("软件设计说明模板细节")).toBeInTheDocument();
  expect(screen.getByText("模板骨架解析")).toBeInTheDocument();
  expect(screen.getByText("编制输出预期")).toBeInTheDocument();
  expect(screen.getByText("模板-规范映射")).toBeInTheDocument();
  expect(screen.queryByText("打开源 PDF")).not.toBeInTheDocument();
  expect(screen.getByText("Architecture Overview")).toBeInTheDocument();
  expect(screen.getByText("用于把 P3 软设章节与军标章节建立对应关系。")).toBeInTheDocument();
});

test("receives a requirement spec as a P3 order and supports rejection", async () => {
  mockP3WorkspaceState({
    initialOrder: false,
    specs: [createRequirementSpec("spec-available", "新型协同规划软件")],
  });

  render(
    <MemoryRouter initialEntries={["/xx-p3"]} future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <App />
    </MemoryRouter>,
  );

  expect(await screen.findByText("新型协同规划软件")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "接收为P3订单" }));
  await waitFor(() =>
    expect(postMock).toHaveBeenCalledWith(
      "/software-design/orders",
      expect.objectContaining({ requirement_spec_id: "spec-available" }),
    ),
  );
  expect((await screen.findAllByText("pending_approval")).length).toBeGreaterThan(0);
  expect(screen.getAllByText("新型协同规划软件").length).toBeGreaterThan(0);
  expect(screen.getByRole("button", { name: "接收为P3订单" })).toBeDisabled();

  fireEvent.click(screen.getByRole("button", { name: /驳\s*回/ }));
  await waitFor(() => expect(screen.getAllByText("rejected").length).toBeGreaterThan(0));
});
