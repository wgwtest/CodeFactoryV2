export type DesignMorphCanvasStageKind = "paper" | "tree" | "architecture" | "table" | "cards";

export type DesignMorphCanvasRenderable = {
  x: number;
  y: number;
  w: number;
  h: number;
  items: string[];
};

export type DesignMorphStageRenderer = (context: CanvasRenderingContext2D, item: DesignMorphCanvasRenderable) => void;

export const DESIGN_MORPH_STAGE_RENDERERS: Record<DesignMorphCanvasStageKind, DesignMorphStageRenderer> = {
  architecture: drawArchitectureItem,
  cards: drawCardsItem,
  paper: drawPaperItem,
  table: drawTableItem,
  tree: drawTreeItem,
};

export function resolveCanvasStageRenderer(kind: string | undefined): DesignMorphStageRenderer {
  if (kind && kind in DESIGN_MORPH_STAGE_RENDERERS) {
    return DESIGN_MORPH_STAGE_RENDERERS[kind as DesignMorphCanvasStageKind];
  }
  return DESIGN_MORPH_STAGE_RENDERERS.paper;
}

function drawPaperItem(context: CanvasRenderingContext2D, item: DesignMorphCanvasRenderable) {
  const top = item.y + 234;
  context.fillStyle = "#f7faf9";
  roundRect(context, item.x + 28, top - 28, item.w - 56, item.h - 270, 6);
  context.fill();
  item.items.slice(0, 6).forEach((line, index) => {
    const y = top + index * 54;
    context.fillStyle = "#14211f";
    context.font = "850 14px Microsoft YaHei, sans-serif";
    context.fillText(`${index + 1}. ${line}`, item.x + 48, y);
    context.strokeStyle = "#d9e3df";
    context.lineWidth = 1;
    context.beginPath();
    context.moveTo(item.x + 48, y + 16);
    context.lineTo(item.x + item.w - 48, y + 16);
    context.stroke();
  });
}

function drawTreeItem(context: CanvasRenderingContext2D, item: DesignMorphCanvasRenderable) {
  const startX = item.x + 52;
  const startY = item.y + 220;
  context.strokeStyle = "#9ab7ae";
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(startX, startY - 22);
  context.lineTo(startX, startY + Math.min(4, item.items.length - 1) * 58);
  context.stroke();
  item.items.slice(0, 5).forEach((line, index) => {
    const y = startY + index * 58;
    context.strokeStyle = "#9ab7ae";
    context.beginPath();
    context.moveTo(startX, y);
    context.lineTo(startX + 34, y);
    context.stroke();
    context.fillStyle = index === 0 ? "#e6f0f4" : "#f6faf8";
    roundRect(context, startX + 34, y - 20, item.w - 104, 40, 6);
    context.fill();
    context.strokeStyle = "#cbd9d4";
    context.stroke();
    context.fillStyle = "#172221";
    context.font = "850 14px Microsoft YaHei, sans-serif";
    context.fillText(line, startX + 50, y + 5);
  });
}

function drawArchitectureItem(context: CanvasRenderingContext2D, item: DesignMorphCanvasRenderable) {
  const labels = item.items.length ? item.items : ["展示层", "功能层", "服务层", "数据层"];
  const top = item.y + 220;
  const layerHeight = 118;
  labels.slice(0, 5).forEach((label, index) => {
    const y = top + index * (layerHeight + 18);
    context.fillStyle = ["#e6f0f4", "#e4f2e9", "#f5e9d6", "#edf2f0", "#f8fbfa"][index] ?? "#f8fbfa";
    roundRect(context, item.x + 34, y, item.w - 68, layerHeight, 8);
    context.fill();
    context.strokeStyle = "#cad8d3";
    context.stroke();
    context.fillStyle = "#143e52";
    context.font = "950 16px Microsoft YaHei, sans-serif";
    context.fillText(label, item.x + 58, y + 32);
    context.fillStyle = "#40514d";
    context.font = "13px Microsoft YaHei, sans-serif";
    wrapCanvasText(context, "模块边界、服务职责、数据依赖和下游投影在本层形成可追溯设计对象。", item.x + 58, y + 62, item.w - 116, 22, 2);
  });
}

function drawTableItem(context: CanvasRenderingContext2D, item: DesignMorphCanvasRenderable) {
  const top = item.y + 218;
  item.items.slice(0, 6).forEach((line, index) => {
    const y = top + index * 54;
    context.fillStyle = index % 2 === 0 ? "#f7faf9" : "#fffdf8";
    context.fillRect(item.x + 28, y, item.w - 56, 48);
    context.strokeStyle = "#d7e0dc";
    context.strokeRect(item.x + 28, y, item.w - 56, 48);
    context.fillStyle = "#172221";
    context.font = "850 14px Microsoft YaHei, sans-serif";
    context.fillText(line, item.x + 48, y + 30);
  });
}

function drawCardsItem(context: CanvasRenderingContext2D, item: DesignMorphCanvasRenderable) {
  const top = item.y + 216;
  const cardWidth = (item.w - 78) / 2;
  item.items.slice(0, 6).forEach((line, index) => {
    const x = item.x + 28 + (index % 2) * (cardWidth + 22);
    const y = top + Math.floor(index / 2) * 106;
    context.fillStyle = "#f8fbfa";
    roundRect(context, x, y, cardWidth, 82, 8);
    context.fill();
    context.strokeStyle = "#d7e0dc";
    context.stroke();
    context.fillStyle = "#172221";
    context.font = "850 14px Microsoft YaHei, sans-serif";
    wrapCanvasText(context, line, x + 16, y + 30, cardWidth - 32, 22, 2);
  });
}

function wrapCanvasText(
  context: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number,
  maxLines: number,
) {
  const chars = text.split("");
  let line = "";
  let lineCount = 0;
  for (const char of chars) {
    const testLine = `${line}${char}`;
    if (context.measureText(testLine).width > maxWidth && line) {
      context.fillText(line, x, y + lineCount * lineHeight);
      line = char;
      lineCount += 1;
      if (lineCount >= maxLines) {
        return;
      }
    } else {
      line = testLine;
    }
  }
  if (line && lineCount < maxLines) {
    context.fillText(line, x, y + lineCount * lineHeight);
  }
}

function roundRect(context: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number) {
  context.beginPath();
  context.moveTo(x + radius, y);
  context.arcTo(x + width, y, x + width, y + height, radius);
  context.arcTo(x + width, y + height, x, y + height, radius);
  context.arcTo(x, y + height, x, y, radius);
  context.arcTo(x, y, x + width, y, radius);
  context.closePath();
}
