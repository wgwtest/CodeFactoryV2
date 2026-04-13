import { createContext, useContext, useEffect, useState } from "react";

import { DEFAULT_ARCHIVE_ID } from "../lib/archiveKnowledge";
import type { KnowledgeArchive } from "../lib/api";
import { activateKnowledgeArchive, getKnowledgeArchives } from "../lib/archives";

const ACTIVE_ARCHIVE_STORAGE_KEY = "code-factory.activeArchiveId";

type ArchiveContextValue = {
  archives: KnowledgeArchive[];
  activeArchiveId: string | null;
  activeArchive: KnowledgeArchive | null;
  loading: boolean;
  error: string | null;
  setActiveArchiveId: (archiveId: string) => Promise<void>;
  refreshArchives: (preferredArchiveId?: string | null) => Promise<void>;
};

const fallbackContext: ArchiveContextValue = {
  archives: [],
  activeArchiveId: DEFAULT_ARCHIVE_ID,
  activeArchive: null,
  loading: false,
  error: null,
  setActiveArchiveId: async () => {},
  refreshArchives: async () => {},
};

const ArchiveContext = createContext<ArchiveContextValue | null>(null);

function readPersistedArchiveId() {
  try {
    return window.localStorage.getItem(ACTIVE_ARCHIVE_STORAGE_KEY);
  } catch {
    return null;
  }
}

function persistArchiveId(archiveId: string | null) {
  try {
    if (archiveId) {
      window.localStorage.setItem(ACTIVE_ARCHIVE_STORAGE_KEY, archiveId);
      return;
    }
    window.localStorage.removeItem(ACTIVE_ARCHIVE_STORAGE_KEY);
  } catch {
    // Ignore local storage failures in tests or restricted browsers.
  }
}

function resolveActiveArchiveId(archives: KnowledgeArchive[], preferredArchiveId?: string | null) {
  const candidateIds = [
    preferredArchiveId,
    readPersistedArchiveId(),
    archives.find((item) => item.is_active)?.archive_id,
    archives[0]?.archive_id,
    DEFAULT_ARCHIVE_ID,
  ].filter(Boolean) as string[];

  for (const archiveId of candidateIds) {
    if (archives.some((item) => item.archive_id === archiveId)) {
      return archiveId;
    }
  }
  return null;
}

export function ArchiveProvider({ children }: { children: React.ReactNode }) {
  const [archives, setArchives] = useState<KnowledgeArchive[]>([]);
  const [activeArchiveId, setActiveArchiveIdState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refreshArchives(preferredArchiveId?: string | null) {
    try {
      const response = await getKnowledgeArchives();
      const nextArchives = response.data;
      const nextActiveArchiveId = resolveActiveArchiveId(nextArchives, preferredArchiveId);
      setArchives(nextArchives);
      setActiveArchiveIdState(nextActiveArchiveId);
      persistArchiveId(nextActiveArchiveId);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载知识库列表失败");
    } finally {
      setLoading(false);
    }
  }

  async function setActiveArchiveId(archiveId: string) {
    await activateKnowledgeArchive(archiveId);
    persistArchiveId(archiveId);
    await refreshArchives(archiveId);
  }

  useEffect(() => {
    void refreshArchives();
  }, []);

  const activeArchive = archives.find((item) => item.archive_id === activeArchiveId) ?? null;

  return (
    <ArchiveContext.Provider
      value={{
        archives,
        activeArchiveId,
        activeArchive,
        loading,
        error,
        setActiveArchiveId,
        refreshArchives,
      }}
    >
      {children}
    </ArchiveContext.Provider>
  );
}

export function useArchiveContext() {
  return useContext(ArchiveContext) ?? fallbackContext;
}
