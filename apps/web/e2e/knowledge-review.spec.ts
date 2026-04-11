import { expect, test } from "@playwright/test";

test("review flow uploads a document and opens explorers", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Upload Source Document" })).toBeVisible();
  await page.getByRole("link", { name: "Governance" }).click();
  await expect(page.getByRole("heading", { name: "Candidate Review Queue" })).toBeVisible();
  await page.getByRole("link", { name: "Knowledge Graph" }).click();
  await expect(page.getByRole("heading", { name: "Knowledge Graph" })).toBeVisible();
});
