import type { P3ReferenceCenter, P3ReferenceTemplate, P3TemplateStandardMapping } from "../../lib/api";

export type SectionBridge = {
  label: string;
  pairText: string;
};

export type P3TemplateDetailModel = {
  template: P3ReferenceTemplate | null;
  mappings: P3TemplateStandardMapping[];
};

export function buildTemplateOutputs(sectionTitles: string[]) {
  const outputs = ["形成面向软件级交付的《软件设计说明》主文档。"];

  if (sectionTitles.some((title) => title.toLowerCase().includes("architecture"))) {
    outputs.push("明确总体架构、交互模式、部署提示与关键设计决策。");
  }
  if (sectionTitles.some((title) => title.toLowerCase().includes("interface"))) {
    outputs.push("沉淀模块边界、外部系统接口和数据交换约束。");
  }
  if (sectionTitles.some((title) => title.toLowerCase().includes("detail"))) {
    outputs.push("下钻到模块职责、数据结构、异常路径和实现约束。");
  }
  if (sectionTitles.some((title) => title.toLowerCase().includes("traceability"))) {
    outputs.push("建立需求、软设章节与模块工单之间的追溯链。");
  }

  return outputs;
}

export function getTemplateDetailModel(
  referenceCenter: P3ReferenceCenter,
  templateId: string | null,
): P3TemplateDetailModel {
  const template = referenceCenter.templates.find((item) => item.template_id === templateId) ?? null;
  const mappings = template
    ? referenceCenter.mappings.filter((mapping) => mapping.template_id === template.template_id)
    : [];

  return { template, mappings };
}

export function buildSectionBridges(
  referenceCenter: P3ReferenceCenter,
  mappings: P3TemplateStandardMapping[],
  sectionTitle: string,
): SectionBridge[] {
  return mappings.flatMap((mapping) =>
    mapping.section_pairs
      .filter((pair) => pair.template_section === sectionTitle)
      .map((pair) => {
        const standard = referenceCenter.standards.find((item) => item.doc_id === mapping.doc_id);
        return {
          label: `${mapping.doc_id}${standard ? ` · ${standard.title}` : ""}`,
          pairText: `${pair.template_section} -> ${pair.standard_section}`,
        };
      }),
  );
}
