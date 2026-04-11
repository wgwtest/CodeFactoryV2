import { expect, test } from "@playwright/test";

test("review flow uploads a document and opens explorers", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "上传源文档" })).toBeVisible();
  await page.getByRole("link", { name: "知识治理" }).click();
  await expect(page.getByRole("heading", { name: "候选知识审核队列" })).toBeVisible();
  await page.getByRole("link", { name: "知识图谱" }).click();
  await expect(page.getByRole("heading", { name: "知识图谱" })).toBeVisible();
});
