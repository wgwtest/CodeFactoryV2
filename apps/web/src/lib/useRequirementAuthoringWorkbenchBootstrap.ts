import { useEffect, useState } from "react";

import type {
  RequirementAuthoringDocumentSummary,
  RequirementAuthoringKnowledgeProvider,
  RequirementAuthoringTemplate,
  RequirementAuthoringWorkbenchConfig,
} from "./api";
import {
  getRequirementAuthoringDocuments,
  getRequirementAuthoringKnowledgeProviders,
  getRequirementAuthoringTemplates,
  getRequirementAuthoringWorkbenchConfig,
} from "./requirementAuthoring";

export type RequirementAuthoringWorkbenchBootstrap = {
  workbenchConfig: RequirementAuthoringWorkbenchConfig | null;
  templates: RequirementAuthoringTemplate[];
  documents: RequirementAuthoringDocumentSummary[];
  knowledgeProviders: RequirementAuthoringKnowledgeProvider[];
  loading: boolean;
  error: string | null;
};

export function useRequirementAuthoringWorkbenchBootstrap(): RequirementAuthoringWorkbenchBootstrap {
  const [workbenchConfig, setWorkbenchConfig] = useState<RequirementAuthoringWorkbenchConfig | null>(null);
  const [templates, setTemplates] = useState<RequirementAuthoringTemplate[]>([]);
  const [documents, setDocuments] = useState<RequirementAuthoringDocumentSummary[]>([]);
  const [knowledgeProviders, setKnowledgeProviders] = useState<RequirementAuthoringKnowledgeProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        const [configResponse, templatesResponse, documentsResponse, providersResponse] = await Promise.all([
          getRequirementAuthoringWorkbenchConfig(),
          getRequirementAuthoringTemplates(),
          getRequirementAuthoringDocuments(),
          getRequirementAuthoringKnowledgeProviders(),
        ]);
        if (cancelled) {
          return;
        }
        setWorkbenchConfig(configResponse.data);
        setTemplates(templatesResponse.data);
        setDocuments(documentsResponse.data);
        setKnowledgeProviders(providersResponse.data.items);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "加载 P2 规格编写配置失败");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { workbenchConfig, templates, documents, knowledgeProviders, loading, error };
}
