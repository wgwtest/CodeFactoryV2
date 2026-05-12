import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { KnowledgeBaseManagementPage } from "../features/p1Clean/modules/knowledgeBaseManagement/page";

const refreshArchivesMock = vi.fn();
const createArchiveMock = vi.fn();
const activateArchiveMock = vi.fn();
const navigateMock = vi.fn();

vi.mock("../context/ArchiveContext", () => ({
  useArchiveContext: () => ({
    archives: [],
    loading: false,
    error: null,
    refreshArchives: refreshArchivesMock,
  }),
}));

vi.mock("../features/p1Clean/modules/knowledgeBaseManagement/api", () => ({
  knowledgeBaseManagementApi: {
    createArchive: (...args: unknown[]) => createArchiveMock(...args),
    activateArchive: (...args: unknown[]) => activateArchiveMock(...args),
  },
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

beforeEach(() => {
  refreshArchivesMock.mockReset();
  createArchiveMock.mockReset();
  activateArchiveMock.mockReset();
  navigateMock.mockReset();
});

test("creates an archive from a local folder path and enters workspace", async () => {
  createArchiveMock.mockResolvedValue({
    data: {
      archive_id: "sales-contracts",
    },
  });
  activateArchiveMock.mockResolvedValue({ data: { archive_id: "sales-contracts" } });
  refreshArchivesMock.mockResolvedValue(undefined);

  render(<KnowledgeBaseManagementPage />);

  expect(screen.queryByRole("button", { name: "选择文件夹导入" })).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "创建知识库" }));
  expect(screen.getByPlaceholderText("E:/project/Web/智能软件生成/知识构建原始材料/体系结构运行测试小规模v3/Mid Term")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("知识库名称"), { target: { value: "Sales Contracts" } });
  fireEvent.change(screen.getByLabelText("资料文件夹路径"), { target: { value: "E:/project/data/contracts" } });
  fireEvent.click(screen.getByRole("button", { name: "创建并进入工作区" }));

  await waitFor(() => {
    expect(createArchiveMock).toHaveBeenCalledWith({
      archive_id: "sales-contracts",
      name: "Sales Contracts",
      source_dir: "E:/project/data/contracts",
      extract_root: undefined,
    });
  });
  expect(activateArchiveMock).toHaveBeenCalledWith("sales-contracts");
  expect(refreshArchivesMock).toHaveBeenCalledWith("sales-contracts");
  expect(navigateMock).toHaveBeenCalledWith("/p1/archives/sales-contracts/overview");
});
