# `superpowers / brainstorming` 正式文档同步策略机测记录

## 1. 机测记录目标

验证本轮是否已经把“`superpowers` / `brainstorming` 不是用户默认审阅源；关键 `spec` 一旦形成确认性内容，必须同轮同步进项目正式文档根”的规则，写入全局工程策略与当前项目本地映射。

## 2. 本轮变更

本轮新增 / 更新文档如下：

- 更新 `/home/wgw/CodexProject/PROJECT-TRA/ENGINEERING_WORK_STRATEGY.md`
- 更新 `/home/wgw/CodexProject/PROJECT-TRA/skills/project-engineering-strategy/references/ENGINEERING_WORK_STRATEGY.md`
- 更新 `DOC/CODEX_DOC/00-本地工程策略映射.md`

## 3. 机测记录项

1. 检查全局策略正文是否明确：
   - `docs/superpowers/` 与 `.superpowers/brainstorm/` 不是默认用户审阅源
   - 用户未对工作层文档反馈，不得被解释为“已看过但未反对”
2. 检查全局策略是否明确写出“关键 `spec` / `plan` / `brainstorming` 必须同轮同步到正式文档根”的触发条件。
3. 检查全局策略是否明确写出“同步前不得宣称正式已更新、不得直接作为正式已确认基线”的状态限制。
4. 检查当前项目本地映射是否已经继承并显式写出上述规则。

## 4. 机测记录结果

### 4.1 全局策略检查

检查结果：

- `/home/wgw/CodexProject/PROJECT-TRA/ENGINEERING_WORK_STRATEGY.md` 已补充：
  - 正式文档根优先于工作层文档
  - `superpowers / brainstorming` 的用户审阅事实源规则
  - 强制同步触发条件
  - 未同步内容的状态限制
  - 同轮提交与交接门槛

### 4.2 技能引用文档检查

检查结果：

- `/home/wgw/CodexProject/PROJECT-TRA/skills/project-engineering-strategy/references/ENGINEERING_WORK_STRATEGY.md` 已同步相同规则，避免技能调用时继续读取旧口径。

### 4.3 当前项目本地映射检查

检查结果：

- `DOC/CODEX_DOC/00-本地工程策略映射.md` 已补充：
  - 当前项目用户默认不会去读 `docs/superpowers/` 或 `.superpowers/brainstorm/`
  - 关键工作层结论必须同轮回写 `DOC/CODEX_DOC/`
  - 设计、计划、机测记录/验收/交接的正式落点映射

## 5. 结论

本轮机测记录通过。

当前状态：

- 全局策略：已更新
- 当前项目本地映射：已更新
- 人工验收状态：待用户确认
