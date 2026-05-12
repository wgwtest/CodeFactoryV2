import { Tag, Typography } from "antd";

export function PageFrame({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <main className="p1-clean-page">
      <section className="p1-clean-titlebar">
        <Tag color="blue">{eyebrow}</Tag>
        <Typography.Title level={1}>{title}</Typography.Title>
        <Typography.Paragraph>{description}</Typography.Paragraph>
      </section>
      {children}
    </main>
  );
}
