import type { MouseEvent as ReactMouseEvent } from "react";

import type { P6ResolvedNodeCard } from "./p6ExperimentConfig";
import type { P6PortalAnchorSide, P6PortalViewNode, P6PortalPosition } from "./p6PortalData";

type P6BlueprintNodeProps = {
  node: P6PortalViewNode;
  position: P6PortalPosition;
  active: boolean;
  emphasized: boolean;
  visiblePins: P6PortalAnchorSide[];
  relationSummary?: string;
  onClick: () => void;
  onDoubleClick: () => void;
  onMouseDown: (event: ReactMouseEvent<HTMLButtonElement>) => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  preview?: boolean;
  cardPresentation?: P6ResolvedNodeCard;
};

function formatFreshnessLabel(freshness: string) {
  if (freshness === "fresh") {
    return "新鲜";
  }
  if (freshness === "stale") {
    return "过期";
  }
  return "未知";
}

export function P6BlueprintNode({
  node,
  position,
  active,
  emphasized,
  visiblePins,
  relationSummary,
  onClick,
  onDoubleClick,
  onMouseDown,
  onMouseEnter,
  onMouseLeave,
  preview = false,
  cardPresentation,
}: P6BlueprintNodeProps) {
  const nodeDomId = preview ? `p6-portal-preview-node-${node.id}` : `p6-portal-node-${node.id}`;
  const resolvedCard: P6ResolvedNodeCard =
    cardPresentation ??
    (node.kind === "module"
      ? {
          templateId: "template-module-status",
          bindingPresetId: "binding-portal-full",
          summary: node.stageCard.summary_line,
          metricsCount: 2,
          showMetrics: true,
          showTimestamp: true,
          showDescription: false,
          showFreshness: true,
          showUserContext: false,
          showUserHints: false,
          showUserAvailability: false,
          showDegraded: Boolean(node.stageCard.degraded_hint),
        }
      : {
          templateId: "template-user-capsule",
          bindingPresetId: null,
          summary: node.summary,
          metricsCount: 0,
          showMetrics: false,
          showTimestamp: false,
          showDescription: false,
          showFreshness: false,
          showUserContext: true,
          showUserHints: true,
          showUserAvailability: true,
          showDegraded: false,
        });
  const moduleMetrics = node.kind === "module" ? node.stageCard.metric_items.slice(0, resolvedCard.metricsCount) : [];
  const className = [
    "p6-blueprint-node",
    node.kind === "user" ? "p6-blueprint-node--user" : "p6-blueprint-node--module",
    preview ? "p6-blueprint-node--preview" : "",
    active ? "is-active" : "",
    emphasized ? "is-emphasized" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      id={nodeDomId}
      key={node.id}
      type="button"
      data-testid={nodeDomId}
      data-active={active ? "true" : "false"}
      data-node-kind={node.kind}
      data-projection-mode={node.projectionMode}
      data-card-template={resolvedCard.templateId}
      data-binding-preset={resolvedCard.bindingPresetId ?? "participant"}
      aria-label={node.title}
      className={className}
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: `${node.width}px`,
        height: `${node.height}px`,
        ["--p6-node-accent" as string]: node.accent,
      }}
      onClick={(event) => {
        event.stopPropagation();
        onClick();
      }}
      onDoubleClick={(event) => {
        event.stopPropagation();
        onDoubleClick();
      }}
      onMouseDown={onMouseDown}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {visiblePins.map((side) => (
        <span key={side} className={`p6-blueprint-node__pin p6-blueprint-node__pin--${side}`} />
      ))}

      <div className="p6-blueprint-node__body">
        {node.kind === "module" ? (
          <>
            <div className="p6-blueprint-node__head">
              <div className="p6-blueprint-node__head-group">
                <span className="p6-blueprint-node__stage">{node.stage}</span>
                <span className="p6-blueprint-node__category">{node.categoryLabel}</span>
              </div>
              <span className={`p6-blueprint-node__badge p6-blueprint-node__badge--${node.stageCard.entry_badge.tone}`}>
                {node.stageCard.entry_badge.label}
              </span>
            </div>

            <div className="p6-blueprint-node__title-row">
              <span className="p6-blueprint-node__title">{node.title}</span>
              {resolvedCard.showFreshness ? (
                <span className="p6-blueprint-node__freshness">{formatFreshnessLabel(node.freshness)}</span>
              ) : null}
            </div>

            <div className="p6-blueprint-node__headline">{node.stageCard.headline_value}</div>
            <p className="p6-blueprint-node__summary">{resolvedCard.summary}</p>

            {resolvedCard.showMetrics ? (
              <div className="p6-blueprint-node__metrics">
                {moduleMetrics.map((metric) => (
                  <span key={metric.metric_key} className="p6-blueprint-node__metric">
                    {metric.metric_label} {metric.metric_value}
                  </span>
                ))}
              </div>
            ) : null}

            {resolvedCard.showDescription ? <div className="p6-blueprint-node__description">{node.description}</div> : null}

            {resolvedCard.showDegraded && node.stageCard.degraded_hint ? (
              <div className="p6-blueprint-node__degraded">{node.stageCard.degraded_hint}</div>
            ) : null}

            <div className="p6-blueprint-node__footer">
              <span className={`p6-blueprint-node__badge p6-blueprint-node__badge--${node.stageCard.health_badge.tone}`}>
                {node.stageCard.health_badge.label}
              </span>
              {resolvedCard.showTimestamp ? (
                <span className="p6-blueprint-node__timestamp">{node.stageCard.timestamp_label}</span>
              ) : null}
            </div>

            {relationSummary ? (
              <div data-testid={`p6-node-relations-${node.id}`} className="p6-blueprint-node__relations">
                {relationSummary}
              </div>
            ) : null}
          </>
        ) : (
          <div className="p6-blueprint-node__user-shell">
            <span className="p6-blueprint-node__user-kicker">{node.participantPayload.role_label}</span>
            <span className="p6-blueprint-node__user-title">{node.participantPayload.title}</span>
            {resolvedCard.showUserContext ? (
              <span className="p6-blueprint-node__user-context">{node.participantPayload.context_label}</span>
            ) : null}
            <span className="p6-blueprint-node__user-summary">{resolvedCard.summary}</span>
            {resolvedCard.showUserHints ? (
              <div className="p6-blueprint-node__user-hints">
                {node.participantPayload.interaction_hints.map((hint) => (
                  <span key={hint} className="p6-blueprint-node__user-hint">
                    {hint}
                  </span>
                ))}
              </div>
            ) : null}
            {resolvedCard.showDescription ? <span className="p6-blueprint-node__description">{node.description}</span> : null}
            {resolvedCard.showUserAvailability ? (
              <span className="p6-blueprint-node__user-status">{node.participantPayload.availability_hint}</span>
            ) : null}
            {relationSummary ? (
              <span data-testid={`p6-node-relations-${node.id}`} className="p6-blueprint-node__user-relations">
                {relationSummary}
              </span>
            ) : null}
          </div>
        )}
      </div>
    </button>
  );
}
