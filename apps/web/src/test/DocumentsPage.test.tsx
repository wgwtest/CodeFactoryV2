import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";

import { DocumentsPage } from "../pages/DocumentsPage";

test("renders upload form and version table", () => {
  render(<DocumentsPage />);
  expect(screen.getByText("Upload Source Document")).toBeInTheDocument();
  expect(screen.getByText("Document Versions")).toBeInTheDocument();
});
