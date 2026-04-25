import { useArchiveContext } from "../context/ArchiveContext";
import { P6BlueprintCanvas } from "../components/p6/P6BlueprintCanvas";

import "./P6PortalPage.css";

export function P6PortalPage() {
  const { activeArchive } = useArchiveContext();

  return <P6BlueprintCanvas archiveName={activeArchive?.name ?? "未选择知识库"} />;
}
