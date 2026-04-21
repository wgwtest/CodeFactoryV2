# `JB_DOC` 来源库 current baseline 刷新交接

## 1. 本轮目标

补齐 `JB_DOC` current baseline 在来源库层的 revision 级官方证据，并把旧主号页的历史状态显式标记出来。

## 2. 本轮已完成内容

- 修正 `scripts/download_jb_standards.py` 的字段解析，改为读取真实 `QuickSearch` 字段 ID
- 增加 `scripts/refresh_jb_current_baseline.py`
- 生成 4 个 revision 级证据条目：
  - `DI-IPSC-81427B`
  - `DI-SESS-81785B`
  - `DI-SESS-80858D`
  - `DI-QCIC-81794A`
- 新增来源库说明文件：
  - `DOC/JB_DOC/99-标准来源库/01-current-baseline修订证据说明.md`
- 将旧主号页状态显式标记：
  - `DI-SESS-80858 -> legacy_base_entry_stale`
  - `DI-QCIC-81794 -> legacy_base_entry_invalid`
- 同步更新 `JB_DOC` 说明层，不再继续写“revision 级来源页仍待刷新”

## 3. 当前剩余问题

- `DI-SESS-80858D / DI-QCIC-81794A` 当前没有稳定可公开访问的 `QuickSearch` 详情页，因此仍以官方 `WMX` PDF / `NOTICE` 直证据为主
- 旧主号页异常虽然已被标记，但后续若能拿到稳定详情页，仍建议补做二次归档

## 4. 当前状态

- 当前状态：待人工验收
