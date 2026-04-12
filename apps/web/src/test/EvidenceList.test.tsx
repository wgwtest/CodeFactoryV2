import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";

import { EvidenceList } from "../components/EvidenceList";

test("renders evidence excerpts with their document titles and empty fallback", () => {
  const { rerender } = render(
    <EvidenceList
      title="证据摘录"
      items={[
        {
          document_id: "doc-1",
          document_title: "NAS AV-1",
          excerpt: "OV-1 excerpt",
        },
      ]}
    />,
  );

  expect(screen.getByRole("heading", { name: "证据摘录" })).toBeInTheDocument();
  expect(screen.getByText("OV-1 excerpt")).toBeInTheDocument();
  expect(screen.getByText("NAS AV-1")).toBeInTheDocument();

  rerender(<EvidenceList title="证据摘录" items={[]} emptyText="暂无证据摘录" />);
  expect(screen.getByText("暂无证据摘录")).toBeInTheDocument();
});
