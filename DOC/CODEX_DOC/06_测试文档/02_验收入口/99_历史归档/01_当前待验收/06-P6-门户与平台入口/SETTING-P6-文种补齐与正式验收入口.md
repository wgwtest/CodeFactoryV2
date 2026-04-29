# `SETTING-P6` 文种补齐与正式验收入口

- 文档角色：`P6` 当前文种与取证类支撑入口
- 原始轮次标识：`2026-04-22-010050`
- 日期：2026-04-22
- 对应范围：`P6` 文种补齐、节点归档和正式验收执行

## 1. 文种补齐

- [x] 已补齐 `P6.1.2 ~ P6.1.4` 节点合同
- [x] 已补齐 `P6.2`、`P6.2.1 ~ P6.2.5` 节点合同
- [x] 已补齐 `P6.3`、`P6.4` 节点合同
- [x] 已补齐以上节点对应验收大纲
- [x] 已补齐 `04_人测记录 / 05_验收结论` 目录

## 1.1 节点级机测补齐

- [x] 已为 `P6 / P6.1 / P6.1.1 ~ P6.1.4 / P6.2 / P6.2.1 ~ P6.2.5 / P6.3 / P6.4` 补齐独立机测记录
- [x] 全部 `14` 个可测节点均已形成节点级机测件
- [x] 各节点合同 `证据链接` 已回链到对应节点机测记录

## 2. 定向测试

- [x] `git diff --check` 通过
- [x] `uv run pytest apps/api/tests/test_p6_api.py -q` 通过
- [x] `corepack pnpm --dir apps/web test src/test/P6PortalPage.test.tsx src/test/P6ObservationPage.test.tsx src/test/p6PortalGeometry.test.ts src/test/AppRoutes.test.tsx` 通过

## 3. 运行态复核

- [x] `/portal` 返回 `200 OK`
- [x] `/observation` 返回 `200 OK`
- [x] `display-baseline / routes / legend` 返回正式配置
- [x] `mock-scenarios / portal-projection / observation-projection` 返回正式投影内容
- [x] `workbench / promotion-candidates / experiments` 返回正式实验对象
- [x] `POST /api/platform-display/experiments` 可登记实验记录

## 4. 当前判定

- [x] `P6` 全树 `14` 个节点均已建立专用人测记录与验结论文种位置
- [x] `P6` 全树可测节点均已完成本轮节点级机测取证
- [ ] 当前尚未形成独立用户人测批注，现有人测记录不得解释为“已完成人测”
- [ ] 当前轮次仍待用户人工确认，不判定为阶段关闭
