import {
  P6_PORTAL_WORLD,
  p6PortalNodes,
  type P6PortalNodeId,
  type P6PortalPosition,
} from "./p6PortalData";

export type P6PortalCameraState = {
  x: number;
  y: number;
  scale: number;
};

export type P6PortalViewportSize = {
  width: number;
  height: number;
};

export const P6_PORTAL_NODE_PADDING = 48;
export const P6_PORTAL_CAMERA_PADDING = 24;
export const P6_PORTAL_MIN_VIEWPORT = {
  width: 960,
  height: 640,
};

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

export function getPortalNodeById(nodeId: P6PortalNodeId) {
  return p6PortalNodes.find((item) => item.id === nodeId) ?? p6PortalNodes[0];
}

export function clampNodePosition(nodeId: P6PortalNodeId, position: P6PortalPosition): P6PortalPosition {
  const node = getPortalNodeById(nodeId);

  return {
    x: clamp(position.x, P6_PORTAL_NODE_PADDING, P6_PORTAL_WORLD.width - node.width - P6_PORTAL_NODE_PADDING),
    y: clamp(position.y, P6_PORTAL_NODE_PADDING, P6_PORTAL_WORLD.height - node.height - P6_PORTAL_NODE_PADDING),
  };
}

export function normalizeViewportSize(viewport: Partial<P6PortalViewportSize>): P6PortalViewportSize {
  const width = viewport.width && viewport.width > 0 ? viewport.width : P6_PORTAL_MIN_VIEWPORT.width;
  const height = viewport.height && viewport.height > 0 ? viewport.height : P6_PORTAL_MIN_VIEWPORT.height;

  return {
    width,
    height,
  };
}

export function clampCameraToWorld(
  camera: P6PortalCameraState,
  viewport: Partial<P6PortalViewportSize>,
): P6PortalCameraState {
  const size = normalizeViewportSize(viewport);
  const minX = Math.min(P6_PORTAL_CAMERA_PADDING, size.width - P6_PORTAL_WORLD.width * camera.scale - P6_PORTAL_CAMERA_PADDING);
  const maxX = P6_PORTAL_CAMERA_PADDING;
  const minY = Math.min(
    P6_PORTAL_CAMERA_PADDING,
    size.height - P6_PORTAL_WORLD.height * camera.scale - P6_PORTAL_CAMERA_PADDING,
  );
  const maxY = P6_PORTAL_CAMERA_PADDING;

  return {
    ...camera,
    x: clamp(camera.x, minX, maxX),
    y: clamp(camera.y, minY, maxY),
  };
}
