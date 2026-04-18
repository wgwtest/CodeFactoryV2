import { Typography } from "antd";

export function P4Hero() {
  return (
    <header
      id="xx-p4-hero"
      className="xx-p4-page-header"
    >
      <Typography.Text id="xx-p4-hero-kicker" className="xx-p4-page-kicker">
        P4 WORKSPACE
      </Typography.Text>
      <div className="xx-p4-page-heading-row">
        <Typography.Title id="xx-p4-hero-title" level={1} className="xx-p4-page-title">
          XX-P4
        </Typography.Title>
        <Typography.Text id="xx-p4-hero-subtitle" className="xx-p4-page-subtitle">
          工具中台 / Tool Hub
        </Typography.Text>
      </div>
      <Typography.Paragraph id="xx-p4-hero-description" className="xx-p4-page-description">
        面向输入工序链、工具仓库与自演进巡检的独立工作区。
      </Typography.Paragraph>
    </header>
  );
}
