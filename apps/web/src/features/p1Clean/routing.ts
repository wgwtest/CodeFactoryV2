import type { P1ModuleDefinition } from "./types";

export function buildP1WorkspacePath(archiveId: string, route = "overview") {
  return `/p1/archives/${archiveId}/${route}`;
}

export function resolveActiveModuleRoute(pathname: string, modules: P1ModuleDefinition[]) {
  const matched = modules.find((module) => pathname.includes(`/${module.route}`));
  if (matched) return matched.route;
  if (pathname.includes("/run")) return "runtime";
  if (pathname.includes("/policy/packages") || pathname.includes("/policy/rules")) return "policy";
  return "overview";
}

export function buildWorkspaceMenuItems(
  archiveId: string,
  modules: P1ModuleDefinition[],
  options: { includeOverview?: boolean } = {},
) {
  const moduleItems = modules
    .slice()
    .sort((left, right) => left.order - right.order)
    .map((module) => ({
      key: buildP1WorkspacePath(archiveId, module.route),
      label: module.navLabel,
    }));

  if (!options.includeOverview) {
    return moduleItems;
  }

  return [
    {
      key: buildP1WorkspacePath(archiveId, "overview"),
      label: "工作区总览",
    },
    ...moduleItems,
  ];
}
