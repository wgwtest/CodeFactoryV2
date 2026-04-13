import { Typography } from "antd";

import { ApplicationRequirementModeler } from "../components/ApplicationRequirementModeler";
import { ValidationWorkspace } from "../components/ValidationWorkspace";
import { useArchiveContext } from "../context/ArchiveContext";

export function ApplicationModelerPage() {
  const { activeArchive } = useArchiveContext();

  return (
    <ValidationWorkspace
      title="应用需求建模器"
      description={
        <Typography.Paragraph style={{ marginBottom: 0 }}>
          面向不懂技术的行业专家，用纯业务语言完成应用需求建模，形成结构化需求对象与 Markdown 投影。
          {activeArchive ? ` 当前知识库：${activeArchive.name}。` : ""}
        </Typography.Paragraph>
      }
    >
      <ApplicationRequirementModeler />
    </ValidationWorkspace>
  );
}
