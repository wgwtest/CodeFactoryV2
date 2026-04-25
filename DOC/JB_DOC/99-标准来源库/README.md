# 标准来源库

本目录用于保存 `JB_DOC` 所依赖的官方标准来源材料。

## 1. 目录结构

- `detail_pages/`
  - QuickSearch 官方详情页 HTML 归档
- `raw/`
  - 从官方影像入口下载的原始 PDF、NOTICE 或官方返回页
- `metadata/`
  - 每个标准对象的本地元数据 JSON
- `manifest.json`
  - 标准对象总清单
- `01-current-baseline修订证据说明.md`
  - current baseline revision 级官方证据说明

## 2. 下载方式

使用脚本：

- `scripts/download_jb_standards.py`
- `scripts/refresh_jb_current_baseline.py`

默认通过本机代理：

- `http://127.0.0.1:10809`

若需要覆盖，可设置环境变量：

- `JB_STANDARD_PROXY`

## 3. 当前用途

本标准来源库主要用于：

- 为 `JB_DOC` 中的候选标准文档提供本地引用依据
- 保存标准对象详情页与原始影像，避免后续检索漂移
- 为 current baseline 的 revision 级标准对象建立直接证据条目
- 作为模板中心扩展时的本地材料仓

## 4. current baseline 说明

对于 `DI-IPSC-81427B / DI-SESS-81785B / DI-SESS-80858D / DI-QCIC-81794A` 这类 revision 级对象，本来源库当前采用两种证据形态：

- 稳定详情页 + 官方 PDF 双证据
- 官方 `WMX` PDF / `NOTICE` 直证据

第二种形态只在稳定 `QuickSearch` 详情页不可公开访问，或旧主号页已经错指到无关对象时使用。具体见：

- `DOC/JB_DOC/99-标准来源库/01-current-baseline修订证据说明.md`
