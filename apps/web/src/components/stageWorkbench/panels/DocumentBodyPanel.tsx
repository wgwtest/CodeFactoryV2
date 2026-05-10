import { A4DocumentSurface } from "../A4DocumentSurface";
import type { StandardDocumentViewModel } from "../models";
import "../stage-document-workbench.css";

type DocumentBodyPanelProps = {
  document: StandardDocumentViewModel;
};

export function DocumentBodyPanel({ document }: DocumentBodyPanelProps) {
  return (
    <div className="stage-document-panel stage-document-body-panel" data-testid="document-body-panel">
      <A4DocumentSurface
        ariaLabel={document.page.ariaLabel}
        title={document.title}
        subtitle={document.subtitle}
        headerLeft={document.page.headerLeft}
        headerRight={document.page.headerRight}
        footerLeft={document.page.footerLeft}
        footerRight={document.page.footerRight}
        structuredSections={document.sections}
        emptyDescription={document.page.emptyDescription}
      />
    </div>
  );
}
