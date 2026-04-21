# `superpowers / brainstorming` 正式文档同步策略交接

## 1. 本轮目标

把“`superpowers` / `brainstorming` 工作层不是用户默认审阅源；关键 `spec` 一旦形成确认性内容，必须同轮同步到项目正式文档根”的规则，上升为全局工程策略，并映射回当前项目正式文档根。

## 2. 本轮已完成内容

- 更新全局策略源文档：
  - `/home/wgw/CodexProject/PROJECT-TRA/ENGINEERING_WORK_STRATEGY.md`
- 更新技能引用文档：
  - `/home/wgw/CodexProject/PROJECT-TRA/skills/project-engineering-strategy/references/ENGINEERING_WORK_STRATEGY.md`
- 更新当前项目本地策略映射：
  - `DOC/CODEX_DOC/00-本地工程策略映射.md`

## 3. 当前固定口径

- `docs/superpowers/` 与 `.superpowers/brainstorm/` 只承担工作层职责，不是默认用户审阅源。
- 用户没有对工作层文档逐条反馈，不能被解释为“已经看过但未反对”。
- 只要 `spec / plan / brainstorming` 中形成会影响实现、计划、验收或长期协作的关键结论，就必须在同一轮同步进项目正式文档根。
- 未同步前，这些内容只能被称为草稿、过程稿或内部推演材料，不能被称为正式设计、正式计划或用户已确认基线。
- 在向用户汇报正式结论、让用户按文档检查、进入编码、编写正式自测/验收/交接文档、执行正式 `git commit / git push` 之前，必须先完成正式文档根同步。

## 4. 后续动作

1. 后续凡是 `docs/superpowers/specs/` 或 `.superpowers/brainstorm/` 中出现新的关键设计结论，都按本轮新增规则同轮回写 `DOC/CODEX_DOC/`。
2. 若其他项目也依赖同一套 `project-engineering-strategy` 技能，应以更新后的全局策略为准补齐各自本地映射。
3. 后续如需对该规则继续细化，优先改全局策略，再同步映射到项目正式文档根。

## 5. 当前状态

- 当前状态：待人工验收
