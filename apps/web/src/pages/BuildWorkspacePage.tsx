import { Typography } from "antd";

import { ValidationWorkspace } from "../components/ValidationWorkspace";

export function BuildWorkspacePage() {
  return (
    <ValidationWorkspace
      title="软件构建系统"
      description={
        <Typography.Paragraph style={{ marginBottom: 0 }}>
          这里将承接软件设计说明、工具中台和组件能力，形成应用构建链与软件输出结果。当前阶段先提供门户入口占位，后续在 P5
          中继续展开。
        </Typography.Paragraph>
      }
    >
      <Typography.Paragraph style={{ marginBottom: 0 }}>
        当前入口已可从门户页进入，后续将在此处承接实际构建、编排与结果展示能力。
      </Typography.Paragraph>
    </ValidationWorkspace>
  );
}
