import type { MouseEvent as ReactMouseEvent } from "react";

import type { P6PortalAnchorSide, P6PortalNode, P6PortalPosition } from "./p6PortalData";

type P6BlueprintNodeProps = {
  node: P6PortalNode;
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
};

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
}: P6BlueprintNodeProps) {
  const className = [
    "p6-blueprint-node",
    node.kind === "user" ? "p6-blueprint-node--user" : "p6-blueprint-node--module",
    active ? "is-active" : "",
    emphasized ? "is-emphasized" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      id={`p6-portal-node-${node.id}`}
      key={node.id}
      type="button"
      data-testid={`p6-portal-node-${node.id}`}
      data-active={active ? "true" : "false"}
      data-node-kind={node.kind}
      data-projection-mode={node.projectionMode}
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
              <span className="p6-blueprint-node__status">{node.status}</span>
            </div>
            <div className="p6-blueprint-node__title">{node.title}</div>
            <p className="p6-blueprint-node__summary">{node.summary}</p>
            <div className="p6-blueprint-node__metrics">
              {node.metrics.map((metric) => (
                <span key={metric} className="p6-blueprint-node__metric">
                  {metric}
                </span>
              ))}
            </div>
            {relationSummary ? (
              <div data-testid={`p6-node-relations-${node.id}`} className="p6-blueprint-node__relations">
                {relationSummary}
              </div>
            ) : null}
          </>
        ) : (
          <div className="p6-blueprint-node__user-shell">
            <span className="p6-blueprint-node__user-kicker">{node.categoryLabel}</span>
            <span className="p6-blueprint-node__user-title">{node.title}</span>
            <span className="p6-blueprint-node__user-summary">{node.summary}</span>
            <span className="p6-blueprint-node__user-status">{node.status}</span>
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
