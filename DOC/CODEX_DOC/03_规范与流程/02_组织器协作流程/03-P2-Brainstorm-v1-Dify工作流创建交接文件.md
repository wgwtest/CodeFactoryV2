# P2 Brainstorm v1 Dify 工作流创建交接文件

> 用途：本文件可直接交给另一个 Codex 会话，让它在 Dify 工作台中创建 `brainstorm-v1-dify-workflow` 真实工作流。
>
> 重要边界：另一个 Codex 会话负责在 Dify 中创建 workflow，不负责修改当前 CodeFactoryV2 工程代码。当前工程已经有本地插件和本地 Dify-shaped workflow 样板，真实 Dify workflow 只需要遵守本文件的输入输出合同。

**日期：** 2026-05-08

**目标插件 ID：**

```text
brainstorm-v1-dify-workflow
```

**目标 workflow ID 建议：**

```text
brainstorm-v1-dify-shaped-workflow
```

**参考文件：**

```text
orchestrators/xg/brainstorm-v1-dify-workflow/workflow.json
DOC/CODEX_DOC/03_规范与流程/01_数据规范/03-P2-Dify工作流输入输出字段规范.md
DOC/CODEX_DOC/03_规范与流程/02_组织器协作流程/02-P2-Brainstorm-v1-Dify工作流搭建规范.md
```

**Dify 官方参考：**

- Workflow API 运行接口：<https://docs.dify.ai/api-reference/workflows/run-workflow>
- Code 节点：<https://docs.dify.ai/en/guides/workflow/node/code>
- Output 节点：<https://docs.dify.ai/en/use-dify/nodes/output>

## 1. 给另一个 Codex 会话的任务说明

你需要在 Dify 工作台中创建一个 Workflow 应用，用于实现 CodeFactoryV2 的 `P2` 需求分析组织器 `brainstorm-v1-dify-workflow`。

这个 workflow 的职责不是直接写完整需求规格说明，而是完成一次需求分析 Turn：

1. 读取用户输入、模板、规格树、工作正文和决策状态。
2. 判断用户输入与当前需求规格章节的关系。
3. 生成 Brainstorm v1 风格的结构化决策状态增量。
4. 将稳定内容投影成需求规格章节正文补丁。
5. 规划下一轮交互问题。
6. 输出一个严格 JSON，供 CodeFactoryV2 adapter 解析。

交付结果应包括：

- Dify workflow 已创建并发布。
- Start 节点输入变量与本文一致。
- 节点名称或节点备注能对应本文的 6 个逻辑节点。
- End/Output 节点能输出 `result_json`。
- `result_json` 是可解析 JSON 字符串，并符合本文第 8 节的最终输出结构。
- 不写入真实 API Key 到任何文件或提示词中。

## 2. Workflow 总体结构

建议按以下节点搭建：

```text
Start
  -> normalize_input        Code
  -> intent_understanding   LLM
  -> decision_state_delta   LLM
  -> document_projection    Code 或 LLM
  -> next_interaction_planning LLM
  -> normalize_output       Code
  -> End / Output
```

节点职责：

| 节点 ID | 类型 | 说明 |
| --- | --- | --- |
| `normalize_input` | Code | 解析 Start 输入里的 JSON 字符串，提取当前章节、问题、锚点和语义输入 |
| `intent_understanding` | LLM | 判断用户输入与当前章节、上一轮问题的关系 |
| `decision_state_delta` | LLM | 生成 Brainstorm v1 决策状态增量 |
| `document_projection` | Code 或 LLM | 生成 `target_anchor_plan`、`document_patch`、`filled_document_text` |
| `next_interaction_planning` | LLM | 生成下一轮问题、快捷选项和规划原因 |
| `normalize_output` | Code | 组装最终 JSON 字符串 `result_json` |
| `End / Output` | Output | 输出 `result_json` |

如果 Dify 版本支持 LLM 结构化输出或 JSON Schema，请开启；如果不支持，必须在 Prompt 中强制“只输出 JSON，不输出 Markdown”。

## 3. Start 节点输入变量

请在 Start 节点创建以下输入变量。复杂对象统一用字符串传入，变量名以 `_json` 结尾。

| 变量名 | 类型建议 | 必填 | 示例 |
| --- | --- | --- | --- |
| `user_input` | text / paragraph | 是 | `这个系统叫空域运算软件，主要解决空域计算分析需求` |
| `normalized_input_json` | paragraph | 是 | `{"input_type":"free_text","semantic":"..."}` |
| `topic` | text | 是 | `空域运算软件需求规格探索` |
| `template_id` | text | 是 | `81433号` |
| `template_content` | paragraph | 否 | 模板 Markdown 文本 |
| `template_structure_json` | paragraph | 是 | `{"spec_tree":[...]}` |
| `active_spec_node_json` | paragraph | 是 | 当前规格树节点 JSON |
| `spec_tree_json` | paragraph | 是 | 完整规格树 JSON |
| `working_document_json` | paragraph | 是 | Lab 临时正文 JSON |
| `decision_state_json` | paragraph | 否 | 决策状态 JSON |
| `previous_interaction_json` | paragraph | 否 | 上一轮交互 JSON |
| `input_relation_json` | paragraph | 否 | 输入关系 JSON |
| `confirmed_facts_json` | paragraph | 否 | 已确认事实 JSON |
| `open_questions_json` | paragraph | 否 | 未闭合问题 JSON |
| `history_summary` | paragraph | 否 | 历史摘要 |
| `write_policy` | text | 是 | `patch_suggestion_only` |
| `expected_output` | text | 否 | `both` |

## 4. normalize_input 节点

类型：Code。

建议使用 Python。输入变量绑定 Start 节点同名变量。

输出变量建议：

| 输出变量 | 含义 |
| --- | --- |
| `context_json` | 归一化后的上下文 JSON 字符串 |
| `semantic` | 本轮语义输入 |
| `active_section` | 当前目标章节 |
| `active_question` | 当前应追问的问题 |
| `active_spec_node_id` | 当前规格节点 ID |
| `anchor_path` | 正文补丁锚点 |
| `write_policy` | 写入策略 |

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
    user_input: str,
    normalized_input_json: str,
    topic: str,
    template_id: str,
    template_content: str = "",
    template_structure_json: str = "{}",
    active_spec_node_json: str = "{}",
    spec_tree_json: str = "[]",
    working_document_json: str = "{}",
    decision_state_json: str = "{}",
    previous_interaction_json: str = "{}",
    input_relation_json: str = "{}",
    confirmed_facts_json: str = "[]",
    open_questions_json: str = "[]",
    history_summary: str = "",
    write_policy: str = "patch_suggestion_only",
    expected_output: str = "both",
) -> dict:
    normalized_input = _loads(normalized_input_json, {})
    active_spec_node = _loads(active_spec_node_json, {})
    input_relation = _loads(input_relation_json, {})
    semantic = str(normalized_input.get("semantic") or user_input or "").strip()
    active_spec_node_id = str(active_spec_node.get("node_id") or "")
    active_section = str(active_spec_node.get("target_section") or "需求规格说明")
    active_question = str(active_spec_node.get("question") or "请继续补充需求规格说明。")
    anchor_path = active_spec_node_id.replace("SPEC-", "", 1) if active_spec_node_id else "REQ-1.1"

    context = {
        "user_input": user_input,
        "semantic": semantic,
        "topic": topic,
        "template_id": template_id,
        "template_content": template_content,
        "template_structure": _loads(template_structure_json, {}),
        "active_spec_node": active_spec_node,
        "active_spec_node_id": active_spec_node_id,
        "active_section": active_section,
        "active_question": active_question,
        "anchor_path": anchor_path,
        "spec_tree": _loads(spec_tree_json, []),
        "working_document": _loads(working_document_json, {}),
        "decision_state": _loads(decision_state_json, {}),
        "previous_interaction": _loads(previous_interaction_json, {}),
        "input_relation": input_relation,
        "confirmed_facts": _loads(confirmed_facts_json, []),
        "open_questions": _loads(open_questions_json, []),
        "history_summary": history_summary,
        "write_policy": write_policy or "patch_suggestion_only",
        "expected_output": expected_output or "both",
    }
    return {
        "context_json": json.dumps(context, ensure_ascii=False),
        "semantic": semantic,
        "active_section": active_section,
        "active_question": active_question,
        "active_spec_node_id": active_spec_node_id,
        "anchor_path": anchor_path,
        "write_policy": context["write_policy"],
    }
```

## 5. intent_understanding 节点

类型：LLM。

输入：

- `normalize_input.context_json`

System Prompt：

```text
你是 CodeFactoryV2 P2 需求分析系统中的 Brainstorm v1 意图理解节点。

你的任务是判断用户本轮输入与当前需求规格章节、上一轮问题、已有决策状态之间的关系。

必须遵守：
- 只输出 JSON，不输出 Markdown。
- 不生成最终需求规格正文。
- 不编造用户未提供的事实。
- 如果用户输入可以投影到当前章节，应明确 target_section_candidates。
- 如果用户输入目标不清，应把问题写入 ambiguities。

输出字段必须为：
{
  "intent_understanding_result": {
    "user_goal_summary": "",
    "input_type": "",
    "relation_to_previous_interaction": "",
    "document_strategy": "decision_state_then_section_projection",
    "target_section_candidates": [],
    "ambiguities": []
  },
  "stage_task_definition": {
    "task_summary": "",
    "target_sections": [],
    "must_output": []
  },
  "confidence": "medium"
}
```

User Prompt：

```text
请基于以下上下文输出意图理解 JSON：

{{ normalize_input.context_json }}
```

## 6. decision_state_delta 节点

类型：LLM。

输入：

- `normalize_input.context_json`
- `intent_understanding.text` 或结构化输出

System Prompt：

```text
你是 CodeFactoryV2 P2 需求分析系统中的 Brainstorm v1 决策状态节点。

你的任务是把用户本轮输入沉淀为结构化决策状态增量，而不是直接写完整文档。

分类规则：
- 用户明确说出的事实进入 confirmed_facts。
- 本轮根据章节目标形成的工作选择进入 confirmed_decisions。
- 不确定但有用的推断进入 tentative_assumptions，不得伪装成事实。
- 仍需用户确认的问题进入 open_questions。
- 用户明确否定或排除的方向进入 rejected_directions。
- 能投影到需求规格章节的落点进入 chapter_projections。
- next_focus 填写下一步最需要用户补充的问题。

必须遵守：
- 只输出 JSON，不输出 Markdown。
- 不编造事实。
- 每个数组项使用 item_id、content、source_turn_id、target_section、status。
- source_turn_id 如果未知，使用 "turn-0001"。

输出字段必须为：
{
  "decision_state_delta": {
    "confirmed_facts": [],
    "confirmed_decisions": [],
    "tentative_assumptions": [],
    "open_questions": [],
    "rejected_directions": [],
    "chapter_projections": [],
    "next_focus": ""
  },
  "confirmed_facts_delta": [],
  "open_questions_delta": [],
  "confidence": "medium"
}
```

User Prompt：

```text
上下文：
{{ normalize_input.context_json }}

意图理解结果：
{{ intent_understanding.text }}

请输出决策状态增量 JSON。
```

## 7. document_projection 节点

推荐类型：Code。这样能保证锚点和补丁结构稳定。

输入：

- `normalize_input.context_json`
- `decision_state_delta.text` 或结构化输出

输出变量：

| 输出变量 | 含义 |
| --- | --- |
| `document_projection_json` | 章节投影 JSON 字符串 |
| `filled_document_text` | 本轮正文片段 |

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


def _first_fact(decision_delta, fallback):
    facts = decision_delta.get("confirmed_facts") or []
    for item in facts:
        if isinstance(item, dict) and str(item.get("content") or "").strip():
            return str(item["content"]).strip()
        if str(item).strip():
            return str(item).strip()
    return fallback


def main(context_json: str, decision_state_delta_json: str) -> dict:
    context = _loads(context_json, {})
    decision_output = _loads(decision_state_delta_json, {})
    decision_delta = decision_output.get("decision_state_delta") or decision_output
    active_section = str(context.get("active_section") or "需求规格说明")
    anchor_path = str(context.get("anchor_path") or "REQ-1.1")
    write_policy = str(context.get("write_policy") or "patch_suggestion_only")
    semantic = _first_fact(decision_delta, str(context.get("semantic") or ""))
    content = (
        f"围绕“{active_section}”，本轮已确认：{semantic}"
        if semantic
        else f"围绕“{active_section}”，本轮已建立需求分析决策状态。"
    )
    projection = {
        "target_anchor_plan": [
            {
                "plan_id": "BRAINSTORM-DIFY-AP-001",
                "decision_type": "append_existing_clause",
                "template_clause_id": anchor_path,
                "canonical_clause_heading": active_section,
                "display_heading": active_section,
                "anchor_path": anchor_path,
                "reason": "使用 Brainstorm v1 决策状态章节投影作为正文锚点。",
                "confidence": "medium",
            }
        ],
        "document_patch": [
            {
                "plan_ref": "BRAINSTORM-DIFY-AP-001",
                "operation": "append_or_update",
                "content": content,
                "write_policy": write_policy,
            }
        ],
        "filled_document_text": content,
        "changed_sections": [active_section],
    }
    return {
        "document_projection_json": json.dumps(projection, ensure_ascii=False),
        "filled_document_text": content,
    }
```

如果必须使用 LLM 节点，也必须输出与上面 `projection` 相同的 JSON 结构。

## 8. next_interaction_planning 节点

类型：LLM。

输入：

- `normalize_input.context_json`
- `decision_state_delta.text`
- `document_projection.document_projection_json`

System Prompt：

```text
你是 CodeFactoryV2 P2 需求分析系统中的下一轮交互规划节点。

你的任务是基于当前活动章节、决策状态增量和正文补丁，生成下一轮用户问题。

必须遵守：
- 只输出 JSON，不输出 Markdown。
- 问题必须服务于补齐需求规格说明。
- 如果当前章节仍缺关键信息，应继续当前章节。
- 如果当前章节已形成可用正文，可以指向规格树下一个 open 节点。
- quick_options 必须是用户可点击的短选项，不写操作说明。

输出字段必须为：
{
  "next_interaction_plan": {
    "planning_strategy": "decision_state_loop",
    "user_message": "",
    "next_question": "",
    "quick_options": [],
    "plan_reason": "",
    "target_spec_nodes": []
  },
  "planning_trace": [],
  "confidence": "medium"
}
```

User Prompt：

```text
上下文：
{{ normalize_input.context_json }}

决策状态增量：
{{ decision_state_delta.text }}

章节正文投影：
{{ document_projection.document_projection_json }}

请输出下一轮交互规划 JSON。
```

## 9. normalize_output 节点

类型：Code。

输入：

- `normalize_input.context_json`
- `intent_understanding.text`
- `decision_state_delta.text`
- `document_projection.document_projection_json`
- `next_interaction_planning.text`

输出变量：

| 输出变量 | 含义 |
| --- | --- |
| `result_json` | 最终给 CodeFactoryV2 adapter 读取的 JSON 字符串 |
| `assistant_message` | 可选调试输出 |
| `next_question` | 可选调试输出 |

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


def _items_to_text(items):
    result = []
    for item in items or []:
        if isinstance(item, dict):
            content = str(item.get("content") or "").strip()
        else:
            content = str(item).strip()
        if content:
            result.append(content)
    return result


def main(
    context_json: str,
    intent_understanding_json: str,
    decision_state_delta_json: str,
    document_projection_json: str,
    next_interaction_planning_json: str,
) -> dict:
    context = _loads(context_json, {})
    intent = _loads(intent_understanding_json, {})
    decision_output = _loads(decision_state_delta_json, {})
    projection = _loads(document_projection_json, {})
    planning_output = _loads(next_interaction_planning_json, {})
    decision_delta = decision_output.get("decision_state_delta") or {}
    planning = planning_output.get("next_interaction_plan") or {}
    active_section = str(context.get("active_section") or "需求规格说明")
    next_question = str(
        planning.get("next_question")
        or decision_delta.get("next_focus")
        or context.get("active_question")
        or "请继续补充需求规格说明。"
    )
    assistant_message = str(
        planning.get("user_message")
        or f"我已把本轮讨论沉淀为结构化决策状态，并投影到：{active_section}。"
    )
    document_patch = projection.get("document_patch") or []
    filled_document_text = str(projection.get("filled_document_text") or "")
    changed_sections = projection.get("changed_sections") or [active_section]
    confirmed_facts_delta = decision_output.get("confirmed_facts_delta") or _items_to_text(decision_delta.get("confirmed_facts"))
    open_questions_delta = decision_output.get("open_questions_delta") or _items_to_text(decision_delta.get("open_questions"))
    result = {
        "assistant_message": assistant_message,
        "next_question": next_question,
        "quick_options": planning.get("quick_options") or [],
        "filled_document_text": filled_document_text,
        "document_patch": document_patch,
        "target_anchor_plan": projection.get("target_anchor_plan") or [],
        "changed_sections": changed_sections,
        "completion_status": "partial",
        "confidence": str(
            planning_output.get("confidence")
            or decision_output.get("confidence")
            or intent.get("confidence")
            or "medium"
        ),
        "confirmed_facts_delta": confirmed_facts_delta,
        "open_questions_delta": open_questions_delta,
        "decision_state_delta": decision_delta,
        "decision_trace": [
            {
                "step": "intent_understanding",
                "decision": "识别用户输入与当前需求规格章节的关系。",
            },
            {
                "step": "decision_state_delta",
                "decision": "将用户输入沉淀为 Brainstorm v1 决策状态增量。",
            },
            {
                "step": "document_projection",
                "decision": "将稳定内容投影为章节正文补丁。",
            },
            {
                "step": "next_interaction_planning",
                "decision": str(planning.get("plan_reason") or "基于决策状态规划下一轮问题。"),
            },
        ],
        "annotations": [
            "该结果来自真实 Dify workflow，应由 CodeFactoryV2 adapter 归一化后进入 P2 会话。"
        ],
        "risks": [],
        "raw_workflow_trace": {
            "workflow_id": "brainstorm-v1-dify-shaped-workflow",
            "nodes": [
                "normalize_input",
                "intent_understanding",
                "decision_state_delta",
                "document_projection",
                "next_interaction_planning",
                "normalize_output",
            ],
        },
    }
    return {
        "result_json": json.dumps(result, ensure_ascii=False),
        "assistant_message": assistant_message,
        "next_question": next_question,
    }
```

## 10. End / Output 节点

End 或 Output 节点至少输出：

| 输出变量 | 来源 |
| --- | --- |
| `result_json` | `normalize_output.result_json` |

可选输出：

| 输出变量 | 来源 |
| --- | --- |
| `assistant_message` | `normalize_output.assistant_message` |
| `next_question` | `normalize_output.next_question` |

CodeFactoryV2 adapter 主要读取 `result_json`。

## 11. 最终 result_json 必须满足的结构

最终 JSON 至少包含：

```json
{
  "assistant_message": "",
  "next_question": "",
  "quick_options": [],
  "filled_document_text": "",
  "document_patch": [],
  "target_anchor_plan": [],
  "changed_sections": [],
  "completion_status": "partial",
  "confidence": "medium",
  "confirmed_facts_delta": [],
  "open_questions_delta": [],
  "decision_state_delta": {
    "confirmed_facts": [],
    "confirmed_decisions": [],
    "tentative_assumptions": [],
    "open_questions": [],
    "rejected_directions": [],
    "chapter_projections": [],
    "next_focus": ""
  },
  "decision_trace": [],
  "annotations": [],
  "risks": [],
  "raw_workflow_trace": {}
}
```

`document_patch` 每项至少包含：

```json
{
  "plan_ref": "BRAINSTORM-DIFY-AP-001",
  "operation": "append_or_update",
  "content": "",
  "write_policy": "patch_suggestion_only"
}
```

`decision_state_delta.confirmed_facts` 每项建议为：

```json
{
  "item_id": "DS-F-001",
  "content": "",
  "source_turn_id": "turn-0001",
  "target_section": "1 总则 / 编写目的",
  "status": "active"
}
```

## 12. 测试输入样例

Start 节点测试输入：

```json
{
  "user_input": "这个系统叫空域运算软件，主要解决空域计算分析需求",
  "normalized_input_json": "{\"input_type\":\"free_text\",\"semantic\":\"这个系统叫空域运算软件，主要解决空域计算分析需求\"}",
  "topic": "空域运算软件需求规格探索",
  "template_id": "81433号",
  "template_content": "# 81433 软件级需求规格模板",
  "template_structure_json": "{}",
  "active_spec_node_json": "{\"node_id\":\"SPEC-REQ-1.1\",\"title\":\"REQ-1.1 编写目的\",\"target_section\":\"1 总则 / 编写目的\",\"question\":\"请先确认软件名称、背景领域和编写目的。\"}",
  "spec_tree_json": "[]",
  "working_document_json": "{\"document_id\":\"lab-working-document\",\"blocks\":[]}",
  "decision_state_json": "{}",
  "previous_interaction_json": "{\"type\":\"none\"}",
  "input_relation_json": "{\"relation\":\"none\"}",
  "confirmed_facts_json": "[]",
  "open_questions_json": "[]",
  "history_summary": "",
  "write_policy": "patch_suggestion_only",
  "expected_output": "both"
}
```

## 13. 测试输出验收

使用第 12 节输入运行 workflow 后，`result_json` 必须满足：

- 是合法 JSON 字符串。
- `assistant_message` 非空。
- `next_question` 非空。
- `filled_document_text` 包含 `空域运算软件`。
- `document_patch[0].content` 包含 `空域运算软件`。
- `document_patch[0].write_policy` 等于 `patch_suggestion_only`。
- `decision_state_delta.confirmed_facts` 至少有一项。
- `decision_trace` 至少有 3 项。
- 不输出 Markdown 包裹符。

## 14. 交付给 CodeFactoryV2 的信息

创建完成后，请回传以下信息给 CodeFactoryV2 主会话：

```text
DIFY_BASE_URL=<不要填真实密钥，只说明服务地址配置方式>
DIFY_WORKFLOW_ID=<真实 workflow/app 标识>
DIFY_RESPONSE_MODE=blocking
```

同时提供：

- Dify workflow 名称。
- 已发布状态。
- Start 输入变量截图或清单。
- End/Output 输出变量清单。
- 一次使用第 12 节样例输入的 `result_json`。

不得在聊天、文档或仓库中粘贴真实 `DIFY_API_KEY`。
