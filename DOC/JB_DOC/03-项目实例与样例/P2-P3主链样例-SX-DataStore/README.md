# P2-P3 主链样例-SX-DataStore

## 1. 目录定位

本目录用于存放基于 `SX-DataStore` 真实项目资料整理的 P2/P3 主链验证样例。该目录不是模板目录，不替代 `DOC/JB_DOC/02-软件工厂产物模板中心/` 中的标准模板。

## 2. 文档清单

- `01-需求规格说明范本-SX-DataStore.md`：用于验证 P2 需求规格生成结果是否能正确覆盖角色、场景、流程、功能、数据、非功能和验收准则。
- `02-软件设计说明范本-SX-DataStore.md`：用于验证 P3 软件设计生成结果是否能从需求转化为架构、前端、后端、对象模型、API、运行流程和质量门。

## 3. 事实源

本样例基于本机项目：

```text
/home/wgw/CodexProject/SX-DataStore
```

主要事实源包括：

- `README.md`
- `package.json`
- `apps/api-server/src/`
- `apps/portal-web/`
- `apps/admin-web/`
- `apps/ai-search-service/main.py`
- `packages/types/src/`
- `packages/page-schema/src/`
- `DOC/CODEX_DOC/01_需求分析/`
- `DOC/CODEX_DOC/02_设计说明/`
- `DOC/CODEX_DOC/03_规范与流程/`

## 4. 使用边界

- 本目录中的文档是“范本/样例”，不是空白模板。
- 不得把完整范本一次性输入给被测组织器。
- 需求规格说明范本只回答需求，不应被当作软件结构设计。
- 软件设计说明范本只回答设计，不应反向改写需求。
- 若后续 `SX-DataStore` 项目设计或代码发生重大变化，应同步刷新本样例。
