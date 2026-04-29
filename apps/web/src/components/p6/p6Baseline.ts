import type { CSSProperties } from "react";

import type { P6PlatformDisplayBaselinePackage } from "../../lib/p6";

export function buildP6CssVariables(
  baseline: P6PlatformDisplayBaselinePackage | null | undefined,
): CSSProperties | undefined {
  if (!baseline) {
    return undefined;
  }

  const { color_tokens, radius_tokens, shadow_tokens, typography_tokens } = baseline.token_set;

  return {
    ["--p6-surface-canvas" as string]: color_tokens.surface_canvas,
    ["--p6-surface-panel" as string]: color_tokens.surface_panel,
    ["--p6-surface-panel-alt" as string]: color_tokens.surface_panel_alt,
    ["--p6-border-strong" as string]: color_tokens.border_strong,
    ["--p6-text-primary" as string]: color_tokens.text_primary,
    ["--p6-text-secondary" as string]: color_tokens.text_secondary,
    ["--p6-state-ready" as string]: color_tokens.state_ready,
    ["--p6-state-warning" as string]: color_tokens.state_warning,
    ["--p6-state-blocked" as string]: color_tokens.state_blocked,
    ["--p6-state-neutral" as string]: color_tokens.state_neutral,
    ["--p6-radius-card" as string]: radius_tokens.card,
    ["--p6-radius-panel" as string]: radius_tokens.panel,
    ["--p6-shadow-card" as string]: shadow_tokens.card,
    ["--p6-shadow-panel" as string]: shadow_tokens.panel,
    ["--p6-font-title" as string]: typography_tokens.title,
    ["--p6-font-body" as string]: typography_tokens.body,
    ["--p6-font-mono" as string]: typography_tokens.mono,
  };
}

export function resolveP6StageName(
  baseline: P6PlatformDisplayBaselinePackage | null | undefined,
  stageId: string,
  fallback: string,
) {
  return baseline?.stage_naming_baseline.stage_name_map[stageId] ?? fallback;
}

export function resolveP6FeedbackCopy(
  baseline: P6PlatformDisplayBaselinePackage | null | undefined,
  key: string,
  fallback: string,
) {
  return baseline?.status_copy_baseline.feedback_copy_map[key] ?? fallback;
}
