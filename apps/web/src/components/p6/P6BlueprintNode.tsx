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

function formatProjectedValue(value: number | string, unit?: string) {
  return `${value}${unit ?? ""}`;
}

function getStageIconLabel(title: string) {
  if (title.includes("知识")) {
    return "知";
  }
  if (title.includes("需求")) {
    return "需";
  }
  if (title.includes("设计")) {
    return "设";
  }
  if (title.includes("工具")) {
    return "工";
  }
  if (title.includes("构建")) {
    return "构";
  }
  return title.slice(0, 1);
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
  const contractUsers = node.kind === "module" ? (node.stageCard.connected_user_items ?? []) : [];
  const contractPorts = node.kind === "module" ? (node.stageCard.flow_port_items ?? []) : [];
  const inputPort = contractPorts.find((port) => port.direction === "input");
  const outputPort = contractPorts.find((port) => port.direction === "output");
  const overallMetrics = node.kind === "module" ? (node.stageCard.system_overall_metric_items ?? []) : [];
  const liveCounters = node.kind === "module" ? (node.stageCard.live_counter_items ?? []) : [];
  const queueProjection = node.kind === "module" ? node.stageCard.queue_projection : null;
  const queueSlotCount = node.id === "p1" ? 8 : 6;
  const queueSlots = Array.from({ length: queueSlotCount }, (_, index) => queueProjection?.items[index] ?? null);
  const contractPortSides = new Set(
    contractPorts.map((port) => (port.direction === "input" ? "left" : "right") as P6PortalAnchorSide),
  );
  const shouldRenderContractCard =
    node.kind === "module" &&
    (overallMetrics.length > 0 || liveCounters.length > 0 || contractUsers.length > 0 || contractPorts.length > 0 || Boolean(queueProjection));
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
      data-route={node.kind === "module" ? (node.route ?? "") : ""}
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
      {node.kind === "module" && contractUsers.length > 0 ? (
        <div className="p6-blueprint-node__user-stack" aria-label={`${node.title} 当前接入用户`}>
          {contractUsers.slice(0, 6).map((user) => (
            <span
              key={user.user_ref}
              className={`p6-blueprint-node__user-block p6-blueprint-node__user-block--${user.activity_state}`}
              title={`${user.role_label} · ${user.activity_state}`}
            >
              {user.display_label}
            </span>
          ))}
        </div>
      ) : null}

      {node.kind === "module" && inputPort ? (
        <span
          className="p6-blueprint-node__flow-port p6-blueprint-node__flow-port--left"
          aria-label={`${inputPort.label} 输入端口`}
          title={`${inputPort.label} · ${inputPort.current_rate}`}
        />
      ) : null}

      {node.kind === "module" && outputPort ? (
        <span
          className="p6-blueprint-node__flow-port p6-blueprint-node__flow-port--right"
          aria-label={`${outputPort.label} 输出端口`}
          title={`${outputPort.label} · ${outputPort.current_rate}`}
        />
      ) : null}

      {visiblePins.map((side) => (
        contractPortSides.has(side) ? null : (
          <span key={side} className={`p6-blueprint-node__pin p6-blueprint-node__pin--${side}`} />
        )
      ))}

      <div className="p6-blueprint-node__body">
        {node.kind === "module" && shouldRenderContractCard ? (
          <>
            <div className="p6-blueprint-node__stage-header">
              <span className="p6-blueprint-node__stage-icon" aria-hidden="true">
                {getStageIconLabel(node.title)}
              </span>
              <span className="p6-blueprint-node__stage-copy">
                <span className="p6-blueprint-node__title">{node.title}</span>
                <span className="p6-blueprint-node__subtitle">{node.description}</span>
              </span>
              <span className={`p6-blueprint-node__health p6-blueprint-node__health--${node.stageCard.health_badge.tone}`}>
                {node.stageCard.health_badge.label}
              </span>
            </div>

            <div className="p6-blueprint-node__overall-grid">
              {overallMetrics.slice(0, 3).map((metric) => (
                <span key={metric.key} className="p6-blueprint-node__overall-item">
                  <small>{metric.label}</small>
                  <strong>{formatProjectedValue(metric.value, metric.unit)}</strong>
                </span>
              ))}
            </div>

            <div className="p6-blueprint-node__live-row">
              {liveCounters.slice(0, 2).map((counter) => (
                <span key={counter.key} className={`p6-blueprint-node__live-item p6-blueprint-node__live-item--${counter.direction}`}>
                  <small>{counter.label}</small>
                  <strong>{formatProjectedValue(counter.value, counter.unit)}</strong>
                </span>
              ))}
            </div>

            {resolvedCard.showDegraded && node.stageCard.degraded_hint ? (
              <div className="p6-blueprint-node__degraded">{node.stageCard.degraded_hint}</div>
            ) : null}

            {relationSummary ? (
              <div data-testid={`p6-node-relations-${node.id}`} className="p6-blueprint-node__relations">
                {relationSummary}
              </div>
            ) : null}
          </>
        ) : node.kind === "module" ? (
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

      {node.kind === "module" && queueProjection ? (
        <div className="p6-blueprint-node__queue-rack" aria-label={`${node.title} ${queueProjection.label}`}>
          <span className="p6-blueprint-node__queue-label">{queueProjection.label}</span>
          <span className="p6-blueprint-node__queue-rail" aria-hidden="true" />
          <div className="p6-blueprint-node__queue-items">
            {queueSlots.map((item, index) => (
              <span
                key={item?.item_id ?? `${node.id}-empty-${index}`}
                className={[
                  "p6-blueprint-node__queue-hook",
                  item ? `p6-blueprint-node__queue-hook--${item.state}` : "p6-blueprint-node__queue-hook--empty",
                ]
                  .filter(Boolean)
                  .join(" ")}
                title={item ? `${item.label} · ${item.state}` : "等待补位"}
              >
                {item ? item.label.slice(0, 1) : ""}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </button>
  );
}
