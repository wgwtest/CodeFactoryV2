import type { ReactNode } from "react";
import { Empty } from "antd";
import "./stage-document-workbench.css";

type A4DocumentSection = {
  section_id: string;
  title: string;
  content: ReactNode;
  status?: string;
};

type A4DocumentSurfaceProps = {
  title?: string;
  subtitle?: string;
  headerLeft: string;
  headerRight: string;
  footerLeft: string;
  footerRight?: string;
  sections?: A4DocumentSection[];
  emptyDescription?: string;
  ariaLabel: string;
};

export function A4DocumentSurface({
  title,
  subtitle,
  headerLeft,
  headerRight,
  footerLeft,
  footerRight = "Page 1",
  sections = [],
  emptyDescription = "尚未生成文档",
  ariaLabel,
}: A4DocumentSurfaceProps) {
  const hasDocument = Boolean(title && sections.length);

  return (
    <article className="a4-document-surface" aria-label={ariaLabel}>
      <div className={`a4-document-page${hasDocument ? "" : " is-empty"}`}>
        {hasDocument ? (
          <>
            <div className="a4-document-meta">
              <span>{headerLeft}</span>
              <span>{headerRight}</span>
            </div>
            <h2 className="a4-document-title">{title}</h2>
            {subtitle ? <div className="a4-document-subtitle">{subtitle}</div> : null}
            {sections.map((section) => (
              <section key={section.section_id} className={`a4-document-section${section.status ? ` is-${section.status}` : ""}`}>
                <h3>{section.title}</h3>
                <p>{section.content}</p>
              </section>
            ))}
            <footer className="a4-document-footer">
              <span>{footerLeft}</span>
              <span>{footerRight}</span>
            </footer>
          </>
        ) : (
          <Empty description={emptyDescription} />
        )}
      </div>
    </article>
  );
}
