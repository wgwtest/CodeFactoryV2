import { Empty } from "antd";
import type React from "react";
import type { StandardDocumentBlockViewModel, StandardDocumentSectionViewModel } from "./models";
import "./stage-document-workbench.css";

type A4DocumentSection = {
  section_id: string;
  title: string;
  content: string;
  status?: string;
  children?: A4DocumentSection[];
};

type NormalizedA4DocumentSection = {
  section_id: string;
  title: string;
  status?: string;
  blocks: StandardDocumentBlockViewModel[];
  children?: NormalizedA4DocumentSection[];
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
  scrollMode?: "self" | "parent";
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
  scrollMode = "self",
  onSelectBlock,
}: A4DocumentSurfaceProps) {
  const normalizedSections: NormalizedA4DocumentSection[] =
    structuredSections?.map((section) => ({
      section_id: section.sectionId,
      title: section.title,
      status: section.status,
      blocks: section.blocks,
      children: section.children?.map((child) => normalizeStructuredSection(child)),
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
      children: section.children?.map((child) => normalizePlainSection(child)),
    }));
  const hasDocument = Boolean(title && normalizedSections.length);
  const isBusy = Boolean(busyState);

  const surfaceClassName = [
    "a4-document-surface",
    hasDocument && !isBusy ? "is-continuous-paper" : "",
    scrollMode === "parent" ? "is-parent-scroll" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const pageClassName = [
    "a4-document-page",
    isBusy ? "is-busy" : "",
    hasDocument && !isBusy ? "is-continuous-paper" : "",
    !hasDocument && !isBusy ? "is-empty" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <article className={surfaceClassName} aria-label={ariaLabel}>
      <div className={pageClassName} data-testid="a4-document-page">
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
            <div className="a4-document-content" data-testid="a4-document-content">
              {normalizedSections.map((section) => (
                <DocumentSection
                  key={section.section_id}
                  level={3}
                  onSelectBlock={onSelectBlock}
                  section={section}
                  selectedBlockId={selectedBlockId}
                />
              ))}
            </div>
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

function normalizeStructuredSection(section: StandardDocumentSectionViewModel): NormalizedA4DocumentSection {
  return {
    section_id: section.sectionId,
    title: section.title,
    status: section.status,
    blocks: section.blocks,
    children: section.children?.map((child) => normalizeStructuredSection(child)),
  };
}

function normalizePlainSection(section: A4DocumentSection): NormalizedA4DocumentSection {
  return {
    ...section,
    blocks: [
      {
        blockId: `${section.section_id}-body`,
        kind: "paragraph",
        content: section.content,
        sourceRefs: [],
        qualityRefs: [],
      },
    ],
    children: section.children?.map((child) => normalizePlainSection(child)),
  };
}

function DocumentSection({
  section,
  level,
  selectedBlockId,
  onSelectBlock,
}: {
  section: NormalizedA4DocumentSection;
  level: 3 | 4 | 5 | 6;
  selectedBlockId?: string;
  onSelectBlock?: (block: StandardDocumentBlockViewModel, section: NormalizedA4DocumentSection) => void;
}) {
  const HeadingTag = `h${level}` as keyof JSX.IntrinsicElements;
  const childLevel = Math.min(level + 1, 6) as 3 | 4 | 5 | 6;
  return (
    <section className={`a4-document-section is-level-${level}${section.status ? ` is-${section.status}` : ""}`}>
      <HeadingTag>{section.title}</HeadingTag>
      {section.blocks.map((block) => (
        <DocumentBlock
          block={block}
          key={block.blockId}
          selected={selectedBlockId === block.blockId}
          onSelect={() => onSelectBlock?.(block, section)}
        />
      ))}
      {section.children?.length ? (
        <div className="a4-document-subsections">
          {section.children.map((child) => (
            <DocumentSection
              key={child.section_id}
              level={childLevel}
              onSelectBlock={onSelectBlock}
              section={child}
              selectedBlockId={selectedBlockId}
            />
          ))}
        </div>
      ) : null}
    </section>
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
  const blockDomId = block.anchorId ?? block.blockId;
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
      <ul className={`a4-document-block-list ${className}`} id={blockDomId} {...selectionProps}>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    );
  }

  if (block.kind === "code") {
    return (
      <pre className={`a4-document-block-code ${className}`} id={blockDomId} {...selectionProps}>
        {block.content}
      </pre>
    );
  }

  if (block.kind === "table") {
    const columns = block.columns?.length ? block.columns : [];
    const rows = block.rows?.length ? block.rows : block.content
      .split("\n")
      .map((row) => row.split("|").map((cell) => cell.trim()).filter(Boolean))
      .filter((row) => row.length);
    return (
      <table
        aria-label={block.title}
        className={`a4-document-block-table ${className}`}
        id={blockDomId}
        {...selectionProps}
      >
        {block.title ? <caption>{block.title}</caption> : null}
        {columns.length ? (
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column} scope="col">{column}</th>
              ))}
            </tr>
          </thead>
        ) : null}
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${block.blockId}-row-${rowIndex + 1}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${block.blockId}-row-${rowIndex + 1}-cell-${cellIndex + 1}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  if (block.kind === "diagram" || block.kind === "diagram_placeholder") {
    return (
      <figure className={`a4-document-block-diagram ${className}`} id={blockDomId} {...selectionProps}>
        {block.title ? <figcaption>{block.title}</figcaption> : null}
        <pre>{block.content}</pre>
        {block.diagramType ? <small>{block.diagramType}</small> : null}
      </figure>
    );
  }

  return (
    <p className={`a4-document-block is-${block.kind} ${className}`} id={blockDomId} {...selectionProps}>
      {block.title ? <strong>{block.title}：</strong> : null}
      {block.content}
    </p>
  );
}
