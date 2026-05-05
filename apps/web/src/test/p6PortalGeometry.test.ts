import { expect, test } from "vitest";

import { P6_PORTAL_WORLD, buildPortalViewNode } from "../components/p6/p6PortalData";
import {
  P6_PORTAL_CAMERA_PADDING,
  P6_PORTAL_NODE_PADDING,
  clampCameraToWorld,
  clampNodePosition,
} from "../components/p6/p6PortalGeometry";

test("clamps node positions inside the portal world frame", () => {
  const nodes = [
    buildPortalViewNode({
      node_id: "p1",
      node_kind: "module",
      title: "业务知识库",
      stage_id: "P1",
      route: "/graph",
      projection_mode: "auto",
      summary: "知识供给稳定对外发布。",
      primary_status: "knowledge_published",
      freshness: "fresh",
      description: "负责沉淀领域知识。",
      stage_card: {
        stage_id: "P1",
        headline_value: "NAS 战术知识库 v3",
        summary_line: "当前知识库已进入对外供给态。",
        metric_items: [],
        entry_badge: { label: "图谱入口可用", tone: "ready" },
        health_badge: { label: "健康", tone: "ready" },
        timestamp_label: "发布于 04-21 09:15",
      },
    }),
  ];

  const clamped = clampNodePosition(nodes, "p1", { x: -160, y: 4000 });

  expect(clamped.x).toBe(P6_PORTAL_NODE_PADDING);
  expect(clamped.y).toBeLessThanOrEqual(P6_PORTAL_WORLD.height - P6_PORTAL_NODE_PADDING);
});

test("clamps camera translation into the visible blueprint boundary", () => {
  const clamped = clampCameraToWorld(
    {
      x: 1200,
      y: -1400,
      scale: 1,
    },
    {
      width: 1280,
      height: 720,
    },
  );

  expect(clamped.x).toBe(P6_PORTAL_CAMERA_PADDING);
  expect(clamped.y).toBeGreaterThanOrEqual(720 - P6_PORTAL_WORLD.height - P6_PORTAL_CAMERA_PADDING);
  expect(clamped.y).toBeLessThanOrEqual(P6_PORTAL_CAMERA_PADDING);
});
