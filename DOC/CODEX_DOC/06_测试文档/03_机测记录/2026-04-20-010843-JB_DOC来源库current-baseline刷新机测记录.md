# `JB_DOC` 来源库 current baseline 刷新机测记录

## 1. 本轮目标

刷新 `DOC/JB_DOC/99-标准来源库/`，为平台 current baseline 中的过程类主文种补齐 revision 级官方证据，并把旧主号页的异常状态显式标记出来。

## 2. 机测记录范围

- `scripts/download_jb_standards.py`
- `scripts/refresh_jb_current_baseline.py`
- `DOC/JB_DOC/99-标准来源库/README.md`
- `DOC/JB_DOC/99-标准来源库/00-标准对象清单.md`
- `DOC/JB_DOC/99-标准来源库/01-current-baseline修订证据说明.md`
- `DOC/JB_DOC/99-标准来源库/manifest.json`
- `DOC/JB_DOC/99-标准来源库/metadata/*.json`
- `DOC/JB_DOC/99-标准来源库/raw/DI-IPSC-81427B-token5746250.pdf`
- `DOC/JB_DOC/99-标准来源库/raw/DI-SESS-81785B-token5792932.pdf`
- `DOC/JB_DOC/99-标准来源库/raw/DI-SESS-80858D-token5763549.pdf`
- `DOC/JB_DOC/99-标准来源库/raw/DI-SESS-80858D-NOTICE1-token5794369.pdf`
- `DOC/JB_DOC/99-标准来源库/raw/DI-QCIC-81794A-token5761211.pdf`
- `DOC/JB_DOC/README.md`
- `DOC/JB_DOC/01-平台自身标准文档/00-平台自身标准文档包总说明.md`
- `DOC/JB_DOC/04-映射与追溯/00-CODEX_DOC到JB_DOC来源映射总表.md`
- `DOC/JB_DOC/04-映射与追溯/01-标准覆盖缺口清单.md`
- `DOC/JB_DOC/04-映射与追溯/02-文种优先级路线图.md`

## 3. 机测记录项

- [x] `download_jb_standards.py` 已能从 QuickSearch 详情页提取真实字段，并可识别错页文档号
- [x] 已生成 `DI-IPSC-81427B / DI-SESS-81785B / DI-SESS-80858D / DI-QCIC-81794A` 四个 revision 级证据条目
- [x] `manifest.json` 中已同时存在 revision 条目与旧主号页状态标记
- [x] `DI-SESS-80858` 已标记为 `legacy_base_entry_stale`
- [x] `DI-QCIC-81794` 已标记为 `legacy_base_entry_invalid`
- [x] `JB_DOC` 正文说明层已不再继续把这件事描述为“revision 级来源页仍待刷新”

## 4. 机测记录方法与结果

### 4.1 脚本语法校验

- 命令：`python3 -m py_compile scripts/download_jb_standards.py scripts/refresh_jb_current_baseline.py`
- 结果：通过

### 4.2 current baseline 刷新执行

- 命令：`python3 scripts/refresh_jb_current_baseline.py`
- 结果：输出 `Refreshed 4 current baseline evidence entries.`

### 4.3 字段解析校验

- 命令：用 `python3` 调用 `scripts.download_jb_standards._extract_field(...)` 读取本地详情页
- 结果：
  - `DI-IPSC-81427-205530.html` 可读出 `DI-IPSC-81427 / Active / 13-MAR-2017`
  - `DI-SESS-81785-276889.html` 可读出 `DI-SESS-81785 / Active / 08-JAN-2025`
  - `DI-QCIC-81794-275987.html` 读出 `ASTM-D2400`，证明错页识别依据成立

### 4.4 manifest 校验

- 命令：用 `python3` 读取 `manifest.json`
- 结果：
  - revision 条目存在：`DI-IPSC-81427B / DI-SESS-81785B / DI-SESS-80858D / DI-QCIC-81794A`
  - 旧主号页状态存在：
    - `DI-SESS-80858 -> legacy_base_entry_stale`
    - `DI-QCIC-81794 -> legacy_base_entry_invalid`

### 4.5 文档口径校验

- 命令：`rg -n "仍待刷新|还没有全部刷新|还未全部补齐" ...`
- 结果：在本轮更新的 `JB_DOC` 正文范围内无命中

## 5. 当前状态

- 当前状态：已机测记录
