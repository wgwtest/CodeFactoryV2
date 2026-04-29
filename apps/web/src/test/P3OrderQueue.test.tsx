import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { P3OrderQueue } from "../components/p3/P3OrderQueue";

test("renders wrapped action controls in a secondary row so long order names keep usable width", () => {
  const onSelectOrder = vi.fn();
  const onApprove = vi.fn();
  const onReject = vi.fn();
  const onGenerateDraft = vi.fn();

  const { container } = render(
    <P3OrderQueue
      orders={[
        {
          order_id: "p3-order-long-name",
          application_name: "空域协同指挥与跨部门流程编排一体化平台软件设计订单名称特别长用于验证排版",
          requirement_spec_id: "spec-long-name",
          status: "pending_approval",
          updated_at: "2026-04-18T03:00:00Z",
        },
      ]}
      selectedOrderId="p3-order-long-name"
      onSelectOrder={onSelectOrder}
      onApprove={onApprove}
      onReject={onReject}
      onGenerateDraft={onGenerateDraft}
    />,
  );

  expect(screen.getByTestId("p3-order-actions-p3-order-long-name")).toHaveStyle({
    display: "flex",
    flexWrap: "wrap",
  });
  expect(container.querySelector(".ant-list-item-action")).not.toBeInTheDocument();

  fireEvent.click(screen.getByText("空域协同指挥与跨部门流程编排一体化平台软件设计订单名称特别长用于验证排版"));
  expect(onSelectOrder).toHaveBeenCalledWith("p3-order-long-name");
});
