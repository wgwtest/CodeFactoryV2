import type { P6PortalArtifact } from "./p6PortalData";

type P6BlueprintArtifactProps = {
  artifact: P6PortalArtifact;
  emphasized: boolean;
};

export function P6BlueprintArtifact({ artifact, emphasized }: P6BlueprintArtifactProps) {
  return (
    <div
      id={`p6-portal-artifact-${artifact.id}`}
      data-testid={`p6-portal-artifact-${artifact.id}`}
      data-artifact-kind="artifact"
      data-projection-mode={artifact.projectionMode}
      className={[
        "p6-portal-artifact",
        `p6-portal-artifact--${artifact.tone}`,
        emphasized ? "is-emphasized" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={{ left: `${artifact.x}px`, top: `${artifact.y}px` }}
    >
      <span className="p6-portal-artifact__category">{artifact.categoryLabel}</span>
      <span className="p6-portal-artifact__title">{artifact.title}</span>
      <span className="p6-portal-artifact__projection">{artifact.projectionMode === "auto" ? "自动投影" : "人工配置"}</span>
    </div>
  );
}
