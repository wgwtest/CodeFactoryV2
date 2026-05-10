import { Empty } from "antd";
import type { StandardDocumentBlockViewModel, StandardDocumentSectionViewModel } from "./models";
import "./stage-document-workbench.css";

type A4DocumentSection = {
  section_id: string;
  title: string;
  content: string;
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
  structuredSections?: StandardDocumentSectionViewModel[];
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
  structuredSections,
  emptyDescription = "尚未生成文档",
  ariaLabel,
}: A4DocumentSurfaceProps) {
  const normalizedSections =
    structuredSections?.map((section) => ({
      section_id: section.sectionId,
      title: section.title,
      status: section.status,
      blocks: section.blocks,
    })) ??
    sections.map((section) => ({
      ...section,
      blocks: [
        {
          blockId: `${section.section_id}-body`,
          kind: "paragraph" as const,
          content: section.content,
          sourceRefs: [],
          qualityRefs: [],
        },
      ],
    }));
  const hasDocument = Boolean(title && normalizedSections.length);

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
            {normalizedSections.map((section) => (
              <section key={section.section_id} className={`a4-document-section${section.status ? ` is-${section.status}` : ""}`}>
                <h3>{section.title}</h3>
                {section.blocks.map((block) => (
                  <DocumentBlock key={block.blockId} block={block} />
                ))}
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

function DocumentBlock({ block }: { block: StandardDocumentBlockViewModel }) {
  if (block.kind === "list") {
    const items = block.content
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
    return (
      <ul className="a4-document-block-list" id={block.anchorId}>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    );
  }

  if (block.kind === "code") {
    return (
      <pre className="a4-document-block-code" id={block.anchorId}>
        {block.content}
      </pre>
    );
  }

  return (
    <p className={`a4-document-block is-${block.kind}`} id={block.anchorId}>
      {block.title ? <strong>{block.title}：</strong> : null}
      {block.content}
    </p>
  );
}
