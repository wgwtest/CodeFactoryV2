# P3 需规转软设 Dify 工作流创建执行文档

> 用途：本文件可直接交给另一个具备 Dify 接口、API 和密钥配置的 Codex 会话，让它在 Dify 工作台中创建 `P3 需规转软设` 真实 workflow。
>
> 重要边界：Dify 工作台开发会话只负责创建、配置、调试和发布 Dify workflow，不负责修改当前 CodeFactoryV2 工程代码。当前工程负责定义 P3 转换器协议、adapter、输入输出校验、页面接入和验收测试。

**日期：** 2026-05-18

**目标转换器 ID 建议：**

```text
requirement-to-sdd-dify-workflow
```

**目标 workflow ID 建议：**

```text
p3-requirement-to-sdd-workflow
```

**对应 CodeFactoryV2 设计依据：**

```text
DOC/CODEX_DOC/02_设计说明/P3_软件设计系统/P3-软件设计系统设计-260518-0041-插件式转换器落地补充案.md
DOC/JB_DOC/03-项目实例与样例/P2-P3主链样例-SX-DataStore/01-需求规格说明范本-SX-DataStore.md
DOC/JB_DOC/03-项目实例与样例/P2-P3主链样例-SX-DataStore/02-软件设计说明范本-SX-DataStore.md
```

## 1. 给 Dify 工作台开发会话的任务说明

你需要在 Dify 工作台中创建一个 Workflow 应用，用于实现 CodeFactoryV2 的 `P3` 软件设计转换器：

```text
P2 冻结需求规格说明包
  -> P3 Dify workflow
    -> 软件设计说明草稿
    -> SoftwareDesignPackage 初稿
    -> 追溯映射
    -> 设计缺口清单
    -> 人工校核项
    -> P4 工单投影候选
```

这个 workflow 的职责不是继续补写需求，也不是直接冻结设计，而是完成一次“需规到软设”的基础转换：

1. 读取冻结需求规格说明正文和结构化需求对象。
2. 识别角色、业务对象、流程、功能项、数据接口、非功能需求、验收准则和待确认项。
3. 将需求元素映射到软件设计说明目标章节。
4. 生成软件设计说明草稿。
5. 生成结构化 `SoftwareDesignPackage` 初稿。
6. 生成需求到设计的追溯映射。
7. 生成设计缺口清单和人工校核项。
8. 输出严格 JSON 字符串 `result_json`，供 CodeFactoryV2 adapter 解析。

交付结果应包括：

- Dify workflow 已创建并发布。
- Start 节点输入变量与本文第 3 节一致。
- 节点名称或节点备注能对应本文第 2 节的逻辑节点。
- End / Output 节点输出 `result_json`。
- `result_json` 是可解析 JSON 字符串，并符合本文第 8 节输出结构。
- 提供一次基于 `SX-DataStore` 样例的测试输出 JSON。
- 不把真实 API Key、私有服务地址或敏感调试信息写入提示词、文档或返回结果。

## 2. Workflow 总体结构

建议按以下逻辑节点搭建：

```text
Start
  -> normalize_input              Code
  -> requirement_section_parse    LLM 或 Code
  -> design_object_extraction     LLM
  -> target_outline_mapping       LLM 或 Code
  -> design_package_compose       LLM
  -> gap_and_review_check         LLM 或 Code
  -> normalize_output             Code
  -> End / Output
```

节点职责：

| 节点 ID | 类型建议 | 说明 |
| --- | --- | --- |
| `normalize_input` | Code | 解析 Start 输入里的 JSON 字符串，形成统一上下文 |
| `requirement_section_parse` | LLM / Code | 识别需求章节、角色、场景、功能、数据接口、非功能和验收准则 |
| `design_object_extraction` | LLM | 生成模块候选、对象模型候选、API 候选、流程候选和质量约束 |
| `target_outline_mapping` | LLM / Code | 将需求元素映射到目标软设章节和设计包形态 |
| `design_package_compose` | LLM | 生成软件设计说明草稿和结构化设计包初稿 |
| `gap_and_review_check` | LLM / Code | 生成设计缺口、风险和人工校核项 |
| `normalize_output` | Code | 组装最终 JSON 字符串 `result_json` |
| `End / Output` | Output | 输出 `result_json` |

如果 Dify 版本支持 LLM 结构化输出或 JSON Schema，请开启；如果不支持，必须在 Prompt 中强制“只输出 JSON，不输出 Markdown”。

## 3. Start 节点输入变量

请在 Start 节点创建以下输入变量。复杂对象统一用字符串传入，变量名以 `_json` 结尾。

| 变量名 | 类型建议 | 必填 | 说明 |
| --- | --- | --- | --- |
| `requirement_document_text` | paragraph | 是 | 冻结需求规格说明正文 |
| `requirement_document_title` | text | 是 | 需求规格说明标题 |
| `standard_document_json` | paragraph | 否 | 标准需求文档结构 JSON |
| `structured_spec_json` | paragraph | 是 | 结构化需求对象 JSON |
| `annotations_json` | paragraph | 否 | 批注、标注和人工说明 |
| `knowledge_binding_json` | paragraph | 否 | 知识绑定摘要 |
| `frozen_trace_json` | paragraph | 否 | 冻结时间、来源、版本和发布信息 |
| `target_design_profile_json` | paragraph | 是 | 目标软设章节结构和设计口径 |
| `conversion_options_json` | paragraph | 是 | 转换策略、粒度、输出风格等 |
| `quality_rules_json` | paragraph | 是 | 追溯、缺口、人工校核和冻结前质量规则 |
| `sx_datastore_requirement_sample` | paragraph | 否 | `SX-DataStore` 需求样例摘要，不应整篇投喂 |
| `sx_datastore_design_sample_outline` | paragraph | 否 | `SX-DataStore` 软设样例结构摘要 |
| `expected_output` | text | 否 | 默认 `design_package_with_document` |

## 4. normalize_input 节点

类型：Code。

建议使用 Python。输入变量绑定 Start 节点同名变量。

输出变量建议：

| 输出变量 | 含义 |
| --- | --- |
| `context_json` | 归一化后的上下文 JSON 字符串 |
| `source_title` | 输入需规标题 |
| `target_design_title` | 目标软设标题 |
| `expected_output` | 期望输出类型 |

代码示例：

```python
import json


def _loads(value, fallback):
    if value is None or value == "":
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def main(
    requirement_document_text: str,
    requirement_document_title: str,
    standard_document_json: str = "{}",
    structured_spec_json: str = "{}",
    annotations_json: str = "[]",
    knowledge_binding_json: str = "{}",
    frozen_trace_json: str = "{}",
    target_design_profile_json: str = "{}",
    conversion_options_json: str = "{}",
    quality_rules_json: str = "{}",
    sx_datastore_requirement_sample: str = "",
    sx_datastore_design_sample_outline: str = "",
    expected_output: str = "design_package_with_document",
) -> dict:
    structured_spec = _loads(structured_spec_json, {})
    target_profile = _loads(target_design_profile_json, {})
    conversion_options = _loads(conversion_options_json, {})
    app_name = (
        structured_spec.get("application", {}).get("name")
        or requirement_document_title.replace("需求规格说明", "").strip()
        or "未命名软件"
    )
    target_design_title = (
        target_profile.get("design_title")
        or f"{app_name}软件设计说明"
    )
    context = {
        "requirement_document_text": requirement_document_text,
        "requirement_document_title": requirement_document_title,
        "standard_document": _loads(standard_document_json, {}),
        "structured_spec": structured_spec,
        "annotations": _loads(annotations_json, []),
        "knowledge_binding": _loads(knowledge_binding_json, {}),
        "frozen_trace": _loads(frozen_trace_json, {}),
        "target_design_profile": target_profile,
        "conversion_options": conversion_options,
        "quality_rules": _loads(quality_rules_json, {}),
        "sx_datastore_requirement_sample": sx_datastore_requirement_sample,
        "sx_datastore_design_sample_outline": sx_datastore_design_sample_outline,
        "application_name": app_name,
        "target_design_title": target_design_title,
        "expected_output": expected_output or "design_package_with_document",
    }
    return {
        "context_json": json.dumps(context, ensure_ascii=False),
        "source_title": requirement_document_title,
        "target_design_title": target_design_title,
        "expected_output": context["expected_output"],
    }
```

## 5. requirement_section_parse 节点

类型：LLM 或 Code。首版可使用 LLM。

输入：

- `normalize_input.context_json`

System Prompt：

```text
你是 CodeFactoryV2 P3 软件设计转换器中的需求解析节点。

你的任务是从冻结需求规格说明中识别可用于软件设计的事实，而不是继续补写需求。

必须遵守：
- 只输出 JSON，不输出 Markdown。
- 不编造需求中不存在的事实。
- 技术框架、目录结构、API 字段如果需求中没有，不得当作需求事实输出。
- 对不充分的信息标记为 gap_candidates。

输出字段必须为：
{
  "parsed_requirement": {
    "application_name": "",
    "roles": [],
    "business_objects": [],
    "business_processes": [],
    "functional_requirements": [],
    "data_interface_requirements": [],
    "non_functional_requirements": [],
    "acceptance_criteria": [],
    "open_items": []
  },
  "gap_candidates": [],
  "confidence": "medium"
}
```

User Prompt：

```text
请基于以下上下文解析需求规格说明，输出严格 JSON：

{{ normalize_input.context_json }}
```

## 6. design_object_extraction 节点

类型：LLM。

输入：

- `normalize_input.context_json`
- `requirement_section_parse.text` 或结构化输出

System Prompt：

```text
你是 CodeFactoryV2 P3 软件设计转换器中的设计对象抽取节点。

你的任务是把需求事实转换为软件设计对象候选，包括模块、对象模型、API 分组、关键流程和质量约束。

必须遵守：
- 只输出 JSON，不输出 Markdown。
- 区分需求事实和设计推导。
- 设计推导必须标记 derivation_type = "inferred_design"。
- 需求原文来源必须保留 source_refs。
- 不把需求章节直接复制为设计章节。

输出字段必须为：
{
  "design_object_candidates": {
    "modules": [],
    "domain_objects": [],
    "api_groups": [],
    "workflow_candidates": [],
    "quality_constraints": [],
    "frontend_candidates": [],
    "backend_candidates": [],
    "integration_candidates": []
  },
  "traceability_seeds": [],
  "gap_candidates": [],
  "confidence": "medium"
}
```

User Prompt：

```text
上下文：
{{ normalize_input.context_json }}

需求解析结果：
{{ requirement_section_parse.text }}

请输出设计对象候选 JSON。
```

## 7. target_outline_mapping 节点

类型：LLM 或 Code。首版可使用 LLM。

输入：

- `normalize_input.context_json`
- `requirement_section_parse.text`
- `design_object_extraction.text`

System Prompt：

```text
你是 CodeFactoryV2 P3 软件设计转换器中的目标章节映射节点。

你的任务是把需求事实和设计对象候选映射到软件设计说明目标章节。

目标软设章节至少包含：
1. 文档目的与设计口径
2. 系统定位
3. 业务目标与边界
4. 总体架构
5. 前端软件设计
6. 后端软件设计
7. 核心对象模型
8. API 设计
9. 关键运行流程
10. 智能能力、模型调用或专项服务设计
11. 设计约束与质量门
12. 目标目录结构
13. 验收口径
14. 面向平台展示与验证输出接口
15. 设计结论

必须遵守：
- 只输出 JSON，不输出 Markdown。
- 每个目标章节要列出 source_refs。
- 如果某章节缺少足够事实，应写入 gap_list。
- 不得把需求文档原章节号当作软设章节号。

输出字段必须为：
{
  "outline_mapping": [],
  "required_sections": [],
  "gap_list": [],
  "confidence": "medium"
}
```

User Prompt：

```text
上下文：
{{ normalize_input.context_json }}

需求解析：
{{ requirement_section_parse.text }}

设计对象候选：
{{ design_object_extraction.text }}

请输出目标软设章节映射 JSON。
```

## 8. design_package_compose 节点

类型：LLM。

输入：

- `normalize_input.context_json`
- `requirement_section_parse.text`
- `design_object_extraction.text`
- `target_outline_mapping.text`

System Prompt：

```text
你是 CodeFactoryV2 P3 软件设计转换器中的设计包生成节点。

你的任务是生成软件设计说明草稿和 SoftwareDesignPackage 初稿。

必须遵守：
- 只输出 JSON，不输出 Markdown。
- 软件设计说明必须是设计文档，不是需求复述。
- 必须包含总体架构、前端、后端、对象模型、API、流程、质量门和验收。
- 每个主要章节必须带 source_refs 或 derivation_type。
- 缺少事实时写入 gap_list，不要编造。
- 输出内容应适合作为人工校核草稿，不得标记为已冻结。

输出字段必须为：
{
  "design_document": {
    "title": "",
    "version_label": "draft",
    "status": "draft",
    "sections": []
  },
  "design_package": {
    "package_id": "",
    "status": "draft",
    "document_projection": {},
    "functional_tree_projection": {},
    "layered_architecture_projection": {},
    "technical_implementation_projection": {},
    "api_projection": {},
    "workflow_projection": {},
    "quality_gate_projection": {},
    "p4_workorder_projection": {}
  },
  "traceability": [],
  "gap_list": [],
  "confidence": "medium"
}
```

User Prompt：

```text
上下文：
{{ normalize_input.context_json }}

需求解析：
{{ requirement_section_parse.text }}

设计对象候选：
{{ design_object_extraction.text }}

章节映射：
{{ target_outline_mapping.text }}

请生成软件设计说明草稿和 SoftwareDesignPackage 初稿 JSON。
```

## 9. gap_and_review_check 节点

类型：LLM 或 Code。首版可使用 LLM。

输入：

- `normalize_input.context_json`
- `design_package_compose.text`

System Prompt：

```text
你是 CodeFactoryV2 P3 软件设计转换器中的设计缺口与人工校核节点。

你的任务是检查生成草稿是否存在阻断缺口、设计风险和人工校核项。

必须遵守：
- 只输出 JSON，不输出 Markdown。
- 不做通过冻结结论。
- 阻断项、警告项和建议项要区分。
- 重点检查：需求追溯、架构完整性、模块边界、对象模型、API 分组、关键流程、非功能约束、P4 投影可用性。

输出字段必须为：
{
  "gap_list": [],
  "review_findings": [],
  "quality_summary": {
    "blocking_count": 0,
    "warning_count": 0,
    "passed_count": 0
  },
  "confidence": "medium"
}
```

User Prompt：

```text
上下文：
{{ normalize_input.context_json }}

设计包草稿：
{{ design_package_compose.text }}

请输出缺口与人工校核 JSON。
```

## 10. normalize_output 节点

类型：Code。

输入：

- `normalize_input.context_json`
- `requirement_section_parse.text`
- `design_object_extraction.text`
- `target_outline_mapping.text`
- `design_package_compose.text`
- `gap_and_review_check.text`

输出变量：

| 输出变量 | 含义 |
| --- | --- |
| `result_json` | 最终给 CodeFactoryV2 adapter 读取的 JSON 字符串 |
| `summary` | 可选调试摘要 |

代码示例：

```python
import json


def _loads(value, fallback):
    if value is None or value == "":
        return fallback
    if isinstance(value, (dict, list)):
        return value
    text = str(value).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except Exception:
        return fallback


def _merge_gaps(*groups):
    result = []
    seen = set()
    for group in groups:
        for item in group or []:
            if not isinstance(item, dict):
                item = {"severity": "warning", "message": str(item)}
            key = str(item.get("gap_id") or item.get("message") or item)
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
    return result


def main(
    context_json: str,
    requirement_section_parse_json: str,
    design_object_extraction_json: str,
    target_outline_mapping_json: str,
    design_package_compose_json: str,
    gap_and_review_check_json: str,
) -> dict:
    context = _loads(context_json, {})
    parsed = _loads(requirement_section_parse_json, {})
    extracted = _loads(design_object_extraction_json, {})
    mapped = _loads(target_outline_mapping_json, {})
    composed = _loads(design_package_compose_json, {})
    checked = _loads(gap_and_review_check_json, {})

    design_document = composed.get("design_document") or {}
    design_package = composed.get("design_package") or {}
    traceability = composed.get("traceability") or extracted.get("traceability_seeds") or []
    gap_list = _merge_gaps(
        parsed.get("gap_candidates"),
        extracted.get("gap_candidates"),
        mapped.get("gap_list"),
        composed.get("gap_list"),
        checked.get("gap_list"),
    )
    review_findings = checked.get("review_findings") or []

    result = {
        "protocol_version": "p3-design-converter-protocol@1",
        "converter": {
            "converter_id": "requirement-to-sdd-dify-workflow",
            "converter_type": "dify_workflow",
            "observability_level": "limited",
        },
        "design_document": design_document,
        "design_package": design_package,
        "traceability": traceability,
        "gap_list": gap_list,
        "review_findings": review_findings,
        "workorder_projection_candidate": design_package.get("p4_workorder_projection") or {},
        "process_output": {
            "annotations": [
                "Dify workflow generated a draft SoftwareDesignPackage for human review.",
                "Result must not be treated as frozen design."
            ],
            "quality_summary": checked.get("quality_summary") or {},
            "source_title": context.get("requirement_document_title") or "",
        },
        "raw_output": {
            "raw_workflow_trace": {
                "workflow_id": "p3-requirement-to-sdd-workflow",
                "nodes": [
                    "normalize_input",
                    "requirement_section_parse",
                    "design_object_extraction",
                    "target_outline_mapping",
                    "design_package_compose",
                    "gap_and_review_check",
                    "normalize_output"
                ]
            }
        },
        "confidence": composed.get("confidence") or checked.get("confidence") or "medium",
        "annotations": checked.get("annotations") or [],
        "risks": checked.get("risks") or [],
    }
    return {
        "result_json": json.dumps(result, ensure_ascii=False),
        "summary": f"generated {len(design_document.get('sections') or [])} design sections"
    }
```

## 11. 最终输出结构要求

End / Output 节点必须输出：

```json
{
  "result_json": "{...JSON string...}"
}
```

`result_json` 解析后必须至少包含：

```json
{
  "protocol_version": "p3-design-converter-protocol@1",
  "converter": {
    "converter_id": "requirement-to-sdd-dify-workflow",
    "converter_type": "dify_workflow",
    "observability_level": "limited"
  },
  "design_document": {
    "title": "",
    "version_label": "draft",
    "status": "draft",
    "sections": []
  },
  "design_package": {
    "package_id": "",
    "status": "draft",
    "document_projection": {},
    "functional_tree_projection": {},
    "layered_architecture_projection": {},
    "technical_implementation_projection": {},
    "api_projection": {},
    "workflow_projection": {},
    "quality_gate_projection": {},
    "p4_workorder_projection": {}
  },
  "traceability": [],
  "gap_list": [],
  "review_findings": [],
  "workorder_projection_candidate": {},
  "process_output": {},
  "raw_output": {},
  "confidence": "medium",
  "annotations": [],
  "risks": []
}
```

## 12. 输出字段细化要求

### 12.1 `design_document.sections`

每个章节建议包含：

```json
{
  "section_id": "architecture",
  "title": "4. 总体架构",
  "content": "章节正文",
  "status": "generated",
  "source_refs": ["REQ-3.3"],
  "derivation_type": "inferred_design"
}
```

`derivation_type` 可选值：

- `requirement_based`：直接来自需求事实。
- `inferred_design`：设计推导。
- `template_required`：目标软设结构要求但需求事实不足。
- `human_review_required`：必须人工补充或确认。

### 12.2 `traceability`

每项建议包含：

```json
{
  "source_ref": "REQ-FR-05",
  "source_title": "资源篮与申请提交",
  "target_type": "module",
  "target_ref": "request-service",
  "target_title": "请求服务模块",
  "mapping_type": "derived_from",
  "confidence": "high"
}
```

### 12.3 `gap_list`

每项建议包含：

```json
{
  "gap_id": "P3-GAP-001",
  "severity": "warning",
  "message": "需求中未明确真实统一身份认证接入方式，软设只能保留接口边界。",
  "source_refs": ["REQ-5.2"],
  "suggested_action": "人工确认身份源、权限模型和审计留存要求。"
}
```

`severity` 可选值：

- `blocking`
- `warning`
- `info`

### 12.4 `review_findings`

每项建议包含：

```json
{
  "finding_id": "P3-REVIEW-001",
  "severity": "warning",
  "target": "API 设计",
  "message": "API 分组已生成，但字段级接口规范仍需人工补充。",
  "requires_human_decision": true
}
```

## 13. 样例验证要求

请用 `SX-DataStore` 样例做一次端到端调试。输入可以来自以下两份文件的摘要：

```text
DOC/JB_DOC/03-项目实例与样例/P2-P3主链样例-SX-DataStore/01-需求规格说明范本-SX-DataStore.md
DOC/JB_DOC/03-项目实例与样例/P2-P3主链样例-SX-DataStore/02-软件设计说明范本-SX-DataStore.md
```

注意：

- 不要把完整两份范本硬编码进 workflow。
- 需求样例用于输入解析测试。
- 软设样例只用于目标结构和质量参照，不允许整篇照抄。

测试输出至少应能体现：

1. 识别消费者、生产者、管理者三类角色上下文。
2. 识别资源对象、资源申请、审批任务、交付订单、资源实例和页面配置。
3. 识别资源发现与申请、维护发布、审批交付、治理接管、页面配置发布流程。
4. 生成前端设计、后端设计、对象模型、API 分组、关键流程和质量门章节。
5. 输出需求到设计的追溯映射。
6. 输出设计缺口和人工校核项。

## 14. 交付给 CodeFactoryV2 的信息

Dify 工作台开发会话完成后，应交付以下信息给 CodeFactoryV2 当前分支：

```text
workflow_name:
workflow_id:
published_workflow_id:
published_at:
input_variables:
output_variable: result_json
sample_result_json_path_or_content:
known_limitations:
recommended_timeout_seconds:
```

不得交付：

- 真实 API Key。
- 私有 Cookie。
- Dify 工作台登录信息。
- 与 workflow 运行无关的敏感服务地址。

## 15. 通过标准

本 Dify workflow 创建任务完成的最低标准：

- workflow 已发布。
- Start 输入变量符合本文第 3 节。
- Output 输出 `result_json`。
- `result_json` 可被 JSON 解析。
- `result_json.design_document.sections` 至少包含目标软设主要章节。
- `result_json.design_package` 至少包含文档、功能树、架构、API、流程、质量门和 P4 候选投影。
- `result_json.traceability` 非空。
- `result_json.gap_list` 和 `result_json.review_findings` 字段存在。
- workflow 不宣称结果已冻结。
- workflow 不写入或输出真实密钥。
