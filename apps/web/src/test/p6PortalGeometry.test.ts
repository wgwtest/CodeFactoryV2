import { expect, test } from "vitest";

import { P6_PORTAL_WORLD } from "../components/p6/p6PortalData";
import {
  P6_PORTAL_CAMERA_PADDING,
  P6_PORTAL_NODE_PADDING,
  clampCameraToWorld,
  clampNodePosition,
} from "../components/p6/p6PortalGeometry";

test("clamps node positions inside the portal world frame", () => {
  const clamped = clampNodePosition("p1", { x: -160, y: 4000 });

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
