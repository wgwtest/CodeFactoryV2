# P3 Design Lab v2 局部沟通与补丁提案补充设计

**日期：** 2026-05-21

**对应节点：**
- `P3 Design Lab`
- `P3` 软件设计系统
- `局部沟通与补丁提案`

## 1. 背景

在初版需规转软设完成后，用户通常还会针对某个章节、段落、功能对象或结构化映射继续提出修正意见。

这一类请求的目标不是重新生成整份软件设计说明，而是：

- 解释当前段落为什么不满意
- 对局部内容提出拆分、补充、重写或归并建议
- 形成可以人工确认的补丁提案
- 保持原始软设正文和设计基线可追溯

因此需要单独设计一条“局部沟通与补丁提案”工作流，并与初版需规转软设工作流分离。

## 2. 设计目标

1. 初版生成和局部修正解耦。
2. 局部修正复用现有 `turns` 接口，不新增一套前端主流程。
3. Dify 只负责生成局部补丁提案的推理结果，CodeFactory 只负责调用与归一化。
4. 保持 `P3DesignTurn` 和 `P3DesignPatch` 的数据结构兼容。
5. 明确远端失败、配置缺失和无效输出时的处理方式。

## 3. 工作流定位

局部工作流的输入是“已有软设草稿 + 指定局部 + 用户修正意图”。

局部工作流的输出是“局部补丁提案 + 解释 + 待确认项”。

它不承担以下职责：

- 不负责初版需规转软设
- 不负责冻结
- 不负责 P4 工单投影生成
- 不直接改写权威软设正文

## 4. CodeFactory 接入点

唯一对外接入点仍是：

```text
POST /api/software-design-v2/sessions/{session_id}/turns
```

当请求满足以下条件时，进入新工作流：

- `turn_type = scoped_design_edit`
- 提供有效 `scope_anchor`
- 当前会话已经有初版软设草稿

其余回合保持原有行为。

## 5. Dify 运行约定

建议使用独立环境变量：

```bash
CODEFACTORY_P3_SCOPED_DIFY_BASE_URL=http://localhost/v1
CODEFACTORY_P3_SCOPED_DIFY_API_KEY=<Dify Console 的 App API Key>
CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID=f2413e20-7cfc-4188-ae7f-7c23eaa353ff
CODEFACTORY_P3_SCOPED_DIFY_TIMEOUT_SECONDS=180
```

运行约定：

- `BASE_URL` 指向 Dify API 根路径。
- `API_KEY` 只能使用 App API Key。
- `WORKFLOW_ID` 可固定某个发布版本，也可不配以走默认发布版本。
- 远端结果统一从 `outputs.result_json` 读取。

## 6. 输入契约

远端工作流的输入应至少包含：

- `session_id`
- `design_title`
- `version_label`
- `scope_anchor`
- `user_input`
- 当前正文局部上下文
- 当前设计基线局部上下文
- `expected_output`

如果有更细的上下文摘要，也可以附加，但不能破坏上述核心字段。

## 7. 输出契约

远端 `result_json` 应归一化为下列局部回合对象：

- `turn_id`
- `turn_type`
- `normalized_intent`
- `assistant_message`
- `scope_anchor`
- `patch_proposal`
- `context_receipt`
- `provider_call_audit`
- `created_at`

其中：

- `patch_proposal` 必须是结构化对象，不能只返回纯文本。
- `provider_call_audit` 要保留 workflow_id 和 run_id 之类的排障信息。
- `assistant_message` 只做给用户看的简短总结。

## 8. 失败策略

### 8.1 配置缺失

如果局部 Dify 配置缺失，允许使用本地补丁提案器兜底，确保页面可用。

### 8.2 远端失败

如果工作流执行失败、超时、返回非 JSON、或 `result_json` 缺失，后端应返回明确错误，不自动切回初版转换路径。

### 8.3 无效补丁

如果远端返回的补丁不包含必要字段，后端应拒绝该结果，并提示用户重新修正。

## 9. 验收标准

1. 局部修正可以通过 `scoped_design_edit` 触发。
2. 初版转换工作流不受影响。
3. `result_json` 是局部工作流唯一必须读取的远端输出变量。
4. 返回对象仍符合现有 turn / patch 视图。
5. CodeFactory 不需要知道 Dify 的内部编排细节。
6. 后续实现可以在不修改前端主结构的前提下接入。
