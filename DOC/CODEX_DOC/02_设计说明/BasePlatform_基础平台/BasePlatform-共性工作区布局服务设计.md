# BasePlatform 共性工作区布局服务设计

**日期：** 2026-06-20
**所属系统：** CodeFactoryV2 Base Platform
**对应需求规格：** `DOC/CODEX_DOC/01_需求分析/03-共性工作区布局服务需求规格说明.md`
**首个接入阶段：** P3 软件设计系统

## 1. 设计目标

共性工作区布局服务用于把各阶段前端工作台的布局状态保存到后端，并在页面刷新、服务重启或多工作树运行时恢复。

本设计采用“统一信封 + 阶段负载”的方式。Base Platform 负责统一存储、查询、更新和删除布局记录；P3、P6 等阶段负责定义自己的 `payload_json` 结构和前端应用逻辑。

## 2. 系统定位

该服务运行在现有 `apps/api` 后端服务内，是 Base Platform 的一个共性模块。

它不是独立微服务，也不是 P3 内部业务模块。首版实现应注册为 FastAPI 路由，并复用当前工程已经存在的 SQLAlchemy、Pydantic、测试夹具和 `Base.metadata.create_all(engine)` 启动机制。

```text
apps/web 工作区组件
  -> /api/workspace-layouts
    -> workspace_layouts service
      -> workspace_layouts repository
        -> workspace_layouts table
```

## 3. 模块划分

后端建议新增以下模块：

| 模块 | 职责 |
| --- | --- |
| `app.workspace_layouts.models` | Pydantic 请求、响应和领域 DTO。 |
| `app.workspace_layouts.repository` | 数据库读写与查询条件封装。 |
| `app.workspace_layouts.service` | 布局创建、更新、设默认、自动当前布局 upsert 等业务规则。 |
| `app.api.routes.workspace_layouts` | HTTP API 路由。 |
| `app.db.models.workspace_layouts` | SQLAlchemy 表模型。 |

前端建议新增：

| 模块 | 职责 |
| --- | --- |
| `apps/web/src/lib/workspaceLayouts.ts` | 通用布局服务 API 调用与类型定义。 |
| `DesignMorphCanvasPlatform` | 接收布局持久化作用域，加载、应用和保存布局。 |
| `P3DesignLabPage` | 为 P3 传入 `scope_type`、`scope_id` 和 `layout_kind`。 |

## 4. 数据模型

### 4.1 表名

```text
workspace_layouts
```

### 4.2 字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| layout_id | string | 布局记录主键。 |
| owner_user_id | string | 用户标识，首版可为 `default`。 |
| scope_type | string | 业务作用域类型。 |
| scope_id | string | 业务作用域标识。 |
| layout_kind | string | 布局类型和大版本。 |
| layout_role | string | 布局角色。 |
| name | string | 布局名称。 |
| is_default | boolean | 是否为默认布局。 |
| payload_schema_version | string | 负载格式版本。 |
| payload | json | 布局负载正文。 |
| created_at | datetime | 创建时间。 |
| updated_at | datetime | 更新时间。 |
| last_used_at | datetime | 最近使用时间。 |

### 4.3 索引建议

首版至少建立以下查询索引：

1. `owner_user_id`
2. `scope_type`
3. `scope_id`
4. `layout_kind`
5. `layout_role`

服务层保证同一 `owner_user_id + scope_type + scope_id + layout_kind` 范围内默认布局唯一。

## 5. 领域对象

### 5.1 WorkspaceLayoutEnvelope

`WorkspaceLayoutEnvelope` 是通用布局信封，对前后端暴露统一结构：

```json
{
  "layout_id": "wsl-...",
  "owner_user_id": "default",
  "scope_type": "p3_design_session",
  "scope_id": "p3dl-...",
  "layout_kind": "p3_design_morph_canvas@1",
  "layout_role": "current_auto",
  "name": "当前布局",
  "is_default": false,
  "payload_schema_version": "p3_design_morph_canvas.v1",
  "payload": {},
  "created_at": "2026-06-20T00:00:00Z",
  "updated_at": "2026-06-20T00:00:00Z",
  "last_used_at": "2026-06-20T00:00:00Z"
}
```

### 5.2 布局角色

| role | 用途 |
| --- | --- |
| `current_auto` | 自动保存的当前工作状态。每个作用域和布局类型只保留一份。 |
| `named_snapshot` | 用户手动记录的命名布局快照。 |
| `user_default` | 用户指定的默认布局。 |
| `system_default` | 系统预置默认布局，首版可不落库。 |

## 6. HTTP API 设计

### 6.1 查询布局

```http
GET /api/workspace-layouts?scope_type=p3_design_session&scope_id=p3dl-1&layout_kind=p3_design_morph_canvas@1
```

返回：

```json
{
  "items": []
}
```

### 6.2 创建布局

```http
POST /api/workspace-layouts
```

请求体：

```json
{
  "owner_user_id": "default",
  "scope_type": "p3_design_session",
  "scope_id": "p3dl-1",
  "layout_kind": "p3_design_morph_canvas@1",
  "layout_role": "named_snapshot",
  "name": "软设工作区布局",
  "is_default": false,
  "payload_schema_version": "p3_design_morph_canvas.v1",
  "payload": {}
}
```

### 6.3 更新布局

```http
PUT /api/workspace-layouts/{layout_id}
```

请求体可更新名称、角色、默认状态、负载版本和负载正文。

### 6.4 删除布局

```http
DELETE /api/workspace-layouts/{layout_id}
```

删除只影响布局记录，不影响业务数据。

### 6.5 设为默认

```http
POST /api/workspace-layouts/{layout_id}/default
```

服务层应取消同一用户、同一作用域、同一布局类型下其他布局的默认状态。

### 6.6 自动当前布局 upsert

```http
PUT /api/workspace-layouts/current
```

该接口用于前端防抖保存当前工作状态。服务层按照 `owner_user_id + scope_type + scope_id + layout_kind + layout_role=current_auto` 查找已有记录；存在则更新，不存在则创建。

## 7. P3 接入设计

P3 首版配置如下：

| 项 | 值 |
| --- | --- |
| scope_type | `p3_design_session` |
| scope_id | P3 软件设计会话 `session_id` |
| layout_kind | `p3_design_morph_canvas@1` |
| payload_schema_version | `p3_design_morph_canvas.v1` |

P3 负载建议结构：

```json
{
  "activeWindowId": "software-design",
  "viewport": {
    "x": 0,
    "y": 0,
    "scale": 1
  },
  "stageLayouts": {},
  "designSessionId": "p3dl-1",
  "stageSignature": "requirement|conversion|design|projection"
}
```

P3 前端加载策略：

1. 页面获得有效 `session_id` 后查询 `/api/workspace-layouts`。
2. 优先应用 `current_auto`。
3. 如果没有 `current_auto`，再应用 `user_default`。
4. 如果没有后端布局，使用组件内置初始布局。
5. 用户手动“记录布局”时创建 `named_snapshot`。
6. 用户拖动、缩放或切换窗口时防抖调用 `/api/workspace-layouts/current`。

## 8. 前端兼容策略

P3 当前 `localStorage` key 为 `p3-design-morph-layouts`。新版本上线后：

1. 后端布局为权威数据。
2. `localStorage` 可作为短期降级缓存。
3. 首次加载时，如果后端没有布局但本地存在快照，可继续在本地选择，也可后续补一键迁移。
4. 后端保存失败时，不应阻塞 P3 主业务操作，但应避免向用户承诺布局已经持久化。

## 9. 错误处理

| 场景 | 处理 |
| --- | --- |
| 布局不存在 | 返回 404。 |
| 查询条件缺失 | 返回 422。 |
| payload 不是 JSON 对象 | 返回 422。 |
| P3 阶段窗口已变化 | 前端按可匹配窗口部分应用，不存在的窗口忽略。 |
| 数据库不可用 | API 返回错误，前端保留当前内存布局并可降级到本地缓存。 |

## 10. 测试设计

后端测试至少覆盖：

1. 创建并查询布局。
2. 自动当前布局 upsert 不产生重复记录。
3. 设置默认布局会取消同范围其他默认布局。
4. 删除布局后查询不到该布局。
5. P3 作用域只是普通 `scope_type`，服务不依赖 P3 专属表。

前端测试至少覆盖：

1. P3 页面为布局组件传入后端持久化作用域。
2. 布局组件加载 `current_auto` 后应用视口和窗口位置。
3. 用户记录布局时调用后端创建命名快照。
4. 布局变更后触发当前布局防抖保存。

## 11. 演进方向

首版完成 P3 接入后，后续可以补充：

1. 用户体系接入，将 `owner_user_id=default` 替换为真实用户。
2. 布局导入导出。
3. 布局模板共享。
4. 布局变更审计。
5. P6 门户和其他阶段工作台接入同一服务。
