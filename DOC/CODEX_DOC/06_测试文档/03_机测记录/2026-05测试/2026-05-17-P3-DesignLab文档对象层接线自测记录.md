# 2026-05-17 P3 Design Lab 文档对象层接线自测记录

## 1. 验证对象

- `apps/web/src/components/stageWorkbench/DesignMorphCanvasPlatform.tsx`
- `apps/web/src/components/stageWorkbench/design-morph-canvas.css`
- `apps/web/src/pages/adapters/p3DesignLabWorkbenchAdapter.ts`
- `apps/web/src/pages/adapters/p3DesignMorphAdapter.ts`
- `apps/web/src/test/DesignMorphCanvasPlatform.test.tsx`
- `apps/web/src/test/P3DesignMorphModel.test.ts`

## 2. 本轮目标

- 让 `需规` 和 `软设文档` 在 P3 Morph 里变成真实文档对象，而不是纯 Canvas 标签。
- 保留 Canvas 作为滑窗和位置投影层。
- 让文档对象支持 `A4 / 编辑区` 两种视图模式。
- 让主页面能看到 `需规 -> 软设文档` 的对象层传递链。

## 3. 执行命令与结果

### 3.1 单测

```bash
corepack pnpm --dir apps/web exec vitest run src/test/DesignMorphCanvasPlatform.test.tsx src/test/P3DesignMorphModel.test.ts
```

结果：

- `P3DesignMorphModel.test.ts` 通过：`2` 个测试通过。
- `DesignMorphCanvasPlatform.test.tsx` 通过：`12` 个测试通过。
- 合计：`14` 个测试全部通过。

### 3.2 构建

```bash
corepack pnpm --dir apps/web build
```

结果：

- `tsc && vite build` 成功。
- 产物正常生成。
- 仅有 Vite chunk size 警告，不影响构建结果。

### 3.3 补丁卫生检查

```bash
git diff --check
```

结果：

- 通过，无 trailing whitespace 或补丁格式问题。

### 3.4 运行态服务检查

```bash
curl -sS http://127.0.0.1:8030/api/health
curl -sSI http://127.0.0.1:5174/p3-design-lab
curl -sS http://127.0.0.1:8060/api/health
curl -sSI http://127.0.0.1:5183/p2-requirement-analysis-lab
curl -sS http://127.0.0.1:8080/api/health
curl -sSI http://127.0.0.1:5191/portal
```

结果：

- P3 API 健康检查返回 `{"status":"ok"}`。
- P3 页面返回 `200 OK`。
- P2 API 健康检查返回 `{"status":"ok"}`。
- P2 页面返回 `200 OK`。
- platform API 健康检查返回 `{"status":"ok"}`。
- platform 页面返回 `200 OK`。

## 4. 浏览器运行态

### 4.1 截图

- 运行态截图：`/tmp/p3-design-lab-runtime.png`
- 分辨率：`1920 x 1110`

### 4.2 观察结论

- 页面顶部仍为 P3 Lab 头部和输入包选择区。
- 中间主区出现 `软设工作区`。
- 左右对象层显示 `需规`、`软设文档`、`功能树`、`分层架构`、`技术实现`、`展示形态`、`P4 投影`。
- `需规` 与 `软设文档` 都呈现为带标题栏、可切换视图和纸面内容的文档对象。
- 对象层与 Canvas 轨迹层同时存在，未出现空白或明显裁切。

## 5. 说明

- 本轮截图使用了浏览器路由拦截的测试数据，目的是验证对象层渲染和交互形态，不代表当前 P3 API 已有真实发布输入包。
- 当前 P3 线上输入包接口 `GET /api/software-design-v2/input-packages` 在未发布 P2 需规时会返回空列表，这是预期行为。

## 6. 结论

本轮实现通过自测。

- 代码通过单测。
- 代码通过构建。
- 运行态页面可访问。
- 文档对象层已经接入 `需规 / 软设文档` 的真实渲染链路。

## 7. 状态

- 当前状态：`已自测，待用户确认`
