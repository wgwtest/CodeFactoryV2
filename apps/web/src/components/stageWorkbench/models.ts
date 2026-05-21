export type StageDocumentWorkbenchIdentity = {
  stage: string;
  documentType: string;
  upstreamStage: string;
  downstreamStage: string;
};

export type StageDocumentWorkbenchHeader = {
  title: string;
  subtitle: string;
  statusLabel: string;
  providerLabel?: string;
  sourceLabel?: string;
};

export type StageDocumentWorkbenchLayout = {
  defaultActiveProductTab: string;
};

export type StageInputFactSectionViewModel = {
  sectionId: string;
  title: string;
  clauses: Array<{
    clauseId: string;
    title: string;
    content: string;
  }>;
};

export type StageInputFactsViewModel = {
  title: string;
  sourceTitle: string;
  readonly: boolean;
  sections: StageInputFactSectionViewModel[];
  relatedDesigns: Array<{
    software_design_id: string;
    title: string;
    version_label: string;
    status: string;
    created_at: string;
    updated_at: string;
  }>;
  emptyDescription: string;
};

export type StandardDocumentBlockKind = "paragraph" | "clause" | "table" | "list" | "code" | "diagram" | "diagram_placeholder";

export type StandardDocumentBlockViewModel = {
  blockId: string;
  kind: StandardDocumentBlockKind;
  title?: string;
  content: string;
  diagramType?: string;
  columns?: string[];
  rows?: string[][];
  anchorId?: string;
  sourceRefs: string[];
  qualityRefs: string[];
};

export type StandardDocumentSectionViewModel = {
  sectionId: string;
  title: string;
  status: string;
  blocks: StandardDocumentBlockViewModel[];
  children?: StandardDocumentSectionViewModel[];
};

export type StandardDocumentViewModel = {
  documentId: string;
  documentType: string;
  title?: string;
  subtitle?: string;
  versionLabel: string;
  status: "empty" | "draft" | "generated" | "frozen";
  page: {
    ariaLabel: string;
    headerLeft: string;
    headerRight: string;
    footerLeft: string;
    footerRight?: string;
    emptyDescription: string;
  };
  sections: StandardDocumentSectionViewModel[];
  annotations: Array<Record<string, unknown>>;
  traceLinks: Array<Record<string, unknown>>;
};

export type StageQualityGateViewModel = {
  status: "not_run" | "running" | "passed" | "warning" | "blocked";
  summary: {
    blockingCount: number;
    warningCount: number;
    passedCount: number;
  };
  gates: Array<{
    itemId: string;
    severity: "info" | "warning" | "critical" | string;
    title: string;
    description: string;
    scope: "input" | "document" | "state" | "projection" | "freeze" | string;
    anchorId?: string;
    suggestedAction?: string;
  }>;
  emptyDescription: string;
};

export type StageOutputProjectionViewModel = {
  targetStage: string;
  packageName: string;
  status: "empty" | "draft" | "ready" | "frozen";
  sourceDocumentId?: string;
  sourceStateId?: string;
  tree?: StageOutputProjectionTreeNodeViewModel;
  items: Array<{
    itemId: string;
    title: string;
    itemType: string;
    description?: string;
    traceRefs: string[];
    readiness: "pending" | "ready" | "blocked" | string;
  }>;
  emptyDescription: string;
};

export type StageOutputProjectionTreeNodeViewModel = {
  nodeId: string;
  title: string;
  nodeType: string;
  description?: string;
  readiness?: "pending" | "ready" | "blocked" | string;
  sourceRefs?: string[];
  dependsOn?: string[];
  acceptance?: string;
  children?: StageOutputProjectionTreeNodeViewModel[];
};

export type StageInteractionViewModel = {
  mode: "cli" | "questionnaire" | "form" | "hybrid";
  title: string;
  description: string;
  runline: Array<{
    key: string;
    label: string;
    state: "idle" | "active" | "done";
  }>;
  policies: Array<{
    key: string;
    label: string;
    value: string;
  }>;
  message: string;
  feed: Array<{
    id: string;
    speaker: string;
    content: string;
  }>;
  composer: {
    ariaLabel: string;
    disabled: boolean;
    submitLabel: string;
  };
  lastTurn?: {
    turnId: string;
    userInput: string;
    interpretedIntent: string;
    affectedScopes: string[];
    stateEffectSummary: string;
    documentEffectSummary: string;
    nextSuggestions: string[];
  };
};

export type StageConversionViewModel = {
  status: string;
  running: boolean;
  elapsedSeconds: number;
  progressNote?: string;
  strategy: string;
  strategyOptions: Array<{
    value: string;
    label: string;
    description: string;
  }>;
  steps: Array<{
    stepId: string;
    title: string;
    description: string;
    status: string;
  }>;
  draftPreview?: {
    title: string;
    versionLabel?: string;
    sections: string[];
  } | null;
  traceabilitySummary?: {
    mappedClauseCount: number;
    targetCount: number;
    pendingConfirmationCount: number;
  } | null;
  emptyDescription: string;
  processOutput?: Record<string, unknown>;
};

export type StageFreezeViewModel = {
  status: "not_ready" | "candidate" | "frozen";
  gates: StageQualityGateViewModel["gates"];
  candidateOutputs: string[];
  frozenRecord?: {
    recordId: string;
    frozenAt: string;
  };
};

export type StageActionViewModel = {
  key: string;
  label: string;
  disabled: boolean;
  loading: boolean;
};

export type StageRuntimeEventViewModel = {
  eventId: string;
  event_type: string;
  eventType: string;
  message: string;
  created_at: string;
  createdAt: string;
};

export type DocumentOutlineViewModel = {
  sections: Array<{
    sectionId: string;
    title: string;
    children?: Array<{
      sectionId: string;
      title: string;
    }>;
  }>;
  baseline?: {
    label: string;
    architectureMode: string;
    moduleCount: number;
    traceabilityCount: number;
    modules: Array<{
      moduleId: string;
      name: string;
    }>;
    functionTree?: {
      treeId?: string;
      title?: string;
      root?: unknown;
    };
    layeredArchitecture?: StageLayeredArchitectureViewModel;
  };
  emptyDescription: string;
};

export type StageLayeredArchitectureComponentViewModel = {
  componentId: string;
  name: string;
  componentType?: string;
  moduleRefs: string[];
  functionRefs: string[];
};

export type StageLayeredArchitectureLayerViewModel = {
  layerId: string;
  name: string;
  responsibility?: string;
  inputs: string[];
  outputs: string[];
  components: StageLayeredArchitectureComponentViewModel[];
};

export type StageLayeredArchitectureMappingViewModel = {
  mappingId: string;
  moduleId: string;
  moduleName: string;
  layerId: string;
  layerName: string;
  responsibility?: string;
  componentRefs: string[];
  functionRefs: string[];
  sourceRefs: string[];
};

export type StageLayeredArchitectureDiagramViewModel = {
  diagramId: string;
  title: string;
  diagramType?: string;
  content?: string;
};

export type StageLayeredArchitectureViewModel = {
  architectureId: string;
  title: string;
  pattern?: string;
  description?: string;
  sourceRefs: string[];
  designRefs: string[];
  layers: StageLayeredArchitectureLayerViewModel[];
  moduleLayerMappings: StageLayeredArchitectureMappingViewModel[];
  diagrams: StageLayeredArchitectureDiagramViewModel[];
};

export type StageDocumentWorkbenchViewModel = {
  identity: StageDocumentWorkbenchIdentity;
  header: StageDocumentWorkbenchHeader;
  layout: StageDocumentWorkbenchLayout;
  inputFacts: StageInputFactsViewModel;
  interaction: StageInteractionViewModel;
  product: StandardDocumentViewModel;
  outline: DocumentOutlineViewModel;
  conversion: StageConversionViewModel;
  quality: StageQualityGateViewModel;
  projection: StageOutputProjectionViewModel;
  freeze: StageFreezeViewModel;
  runtimeEvents: StageRuntimeEventViewModel[];
  actions: StageActionViewModel[];
};
