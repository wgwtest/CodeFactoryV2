import { Empty } from "antd";
import type React from "react";
import type { StandardDocumentBlockViewModel, StandardDocumentSectionViewModel } from "./models";
import "./stage-document-workbench.css";

type A4DocumentSection = {
  section_id: string;
  title: string;
  content: string;
  status?: string;
};

type NormalizedA4DocumentSection = {
  section_id: string;
  title: string;
  status?: string;
  blocks: StandardDocumentBlockViewModel[];
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
  busyState?: {
    title: string;
    description: string;
    detail?: string;
    elapsedLabel?: string;
    estimateLabel?: string;
    testId?: string;
  };
  ariaLabel: string;
  selectedBlockId?: string;
  onSelectBlock?: (block: StandardDocumentBlockViewModel, section: NormalizedA4DocumentSection) => void;
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
  busyState,
  ariaLabel,
  selectedBlockId,
  onSelectBlock,
}: A4DocumentSurfaceProps) {
  const normalizedSections: NormalizedA4DocumentSection[] =
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
      <div className={`a4-document-page${busyState ? " is-busy" : hasDocument ? "" : " is-empty"}`}>
        {busyState ? (
          <div className="a4-document-busy-state" data-testid={busyState.testId}>
            <span className="a4-document-busy-spinner" aria-hidden="true" />
            <div>
              <strong>{busyState.title}</strong>
              <p>{busyState.description}</p>
              {busyState.elapsedLabel || busyState.estimateLabel ? (
                <div className="a4-document-busy-metrics">
                  {busyState.elapsedLabel ? <span>{busyState.elapsedLabel}</span> : null}
                  {busyState.estimateLabel ? <span>{busyState.estimateLabel}</span> : null}
                </div>
              ) : null}
              {busyState.detail ? <small>{busyState.detail}</small> : null}
            </div>
          </div>
        ) : hasDocument ? (
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
                  <DocumentBlock
                    block={block}
                    key={block.blockId}
                    selected={selectedBlockId === block.blockId}
                    onSelect={() => onSelectBlock?.(block, section)}
                  />
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

function DocumentBlock({
  block,
  selected,
  onSelect,
}: {
  block: StandardDocumentBlockViewModel;
  selected: boolean;
  onSelect: () => void;
}) {
  const selectionProps = {
    "data-selection-id": block.blockId,
    "data-testid": `a4-document-block-${block.blockId}`,
    onClick: (event: React.MouseEvent) => {
      event.stopPropagation();
      onSelect();
    },
  };
  const className = `a4-document-selectable-block${selected ? " is-selected" : ""}`;

  if (block.kind === "list") {
    const items = block.content
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
    return (
      <ul className={`a4-document-block-list ${className}`} id={block.anchorId} {...selectionProps}>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    );
  }

  if (block.kind === "code") {
    return (
      <pre className={`a4-document-block-code ${className}`} id={block.anchorId} {...selectionProps}>
        {block.content}
      </pre>
    );
  }

  return (
    <p className={`a4-document-block is-${block.kind} ${className}`} id={block.anchorId} {...selectionProps}>
      {block.title ? <strong>{block.title}：</strong> : null}
      {block.content}
    </p>
  );
}
