import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";

import { GovernancePage } from "../pages/GovernancePage";

test("renders candidate review queue", () => {
  render(<GovernancePage />);
  expect(screen.getByText("Candidate Review Queue")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Publish Version" })).toBeInTheDocument();
});
