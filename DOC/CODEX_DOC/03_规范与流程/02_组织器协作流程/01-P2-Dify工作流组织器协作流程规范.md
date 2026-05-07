# P2 Dify 工作流组织器协作流程规范

> 归档说明：本文件作为 `P2` 与 Dify 工作台之间的协作流程规范。它说明当前工程、Dify 工作终端、联调过程和验收责任如何分工。
>
> 维护规则：新增 Dify 型组织器时，应先确认是否复用本流程；若改变 PR 分支与 Dify 工作台之间的责任边界，必须回写本文件。

**日期：** 2026-05-07

**适用范围：**

- `P2` 需求分析系统
- Dify workflow 型组织器
- 当前工程 PR 分支
- Dify 工作终端

## 1. 协作模式

当前工程不直接编辑 Dify 工作台里的 workflow。当前工程负责定义合同、字段、示例、adapter 和本地 fallback；Dify 工作终端负责按规范创建、配置、发布真实 workflow。

协作链路如下：

```text
P2 页面
  -> 当前工程 adapter
  -> Dify Workflow API
  -> Dify 返回结构化 JSON
  -> adapter 归一化为组织器合同
  -> P2 页面展示结果、状态和过程数据
```

## 2. 当前工程职责

当前工程负责：

- 定义组织器插件公共输入输出合同。
- 定义 Dify workflow 输入变量和输出 JSON 字段。
- 提供每个 Dify 型组织器的专项搭建规范。
- 提供插件 manifest、adapter 和测试。
- 在没有真实 Dify 配置时提供本地 Dify-shaped workflow 或明确错误。
- 校验 Dify 返回结果并归一化为 `OrchestratorRunResult`。

当前工程不负责：

- 在 Dify 工作台内创建节点。
- 在 Dify 工作台内维护 LLM Prompt。
- 直接保存真实 Dify API Key。
- 把 Dify 内部节点状态强行等同于本地全观测组织器状态。

## 3. Dify 工作终端职责

Dify 工作终端负责：

- 创建 workflow。
- 按专项规范配置输入变量。
- 按专项规范配置 LLM 节点、代码节点、条件分支和输出节点。
- 发布 workflow。
- 提供联调所需的 Dify 服务地址、workflow/app 信息和 API Key。
- 在 Dify 内维护 Prompt 版本和节点配置。

## 4. 文档分层

Dify 组织器相关文档分三层：

| 层级 | 位置 | 作用 |
| --- | --- | --- |
| 公共插件合同 | `03_规范与流程/01_数据规范/02-P2-组织器插件输入输出合同规范.md` | 所有组织器必须遵守 |
| Dify 字段规范 | `03_规范与流程/01_数据规范/03-P2-Dify工作流输入输出字段规范.md` | 所有 Dify 型组织器共享 |
| 单组织器搭建规范 | `03_规范与流程/02_组织器协作流程/*-Dify工作流搭建规范.md` | 具体 workflow 的节点和策略 |

插件目录内的 `ORCHESTRATOR.md`、`workflow.json` 是运行包自带说明，不替代正式文档入口。

## 5. 开发阶段

### 5.1 阶段一：本地 Dify-shaped workflow

目标：

- 固定插件合同。
- 固定字段映射。
- 固定页面挂载路径。
- 不依赖真实 Dify 环境。

交付物：

- 插件目录。
- `manifest.json`。
- `workflow.json`。
- 本地 adapter。
- 后端测试。

### 5.2 阶段二：Dify 工作台搭建

目标：

- 在 Dify 中创建真实 workflow。
- 按专项规范配置节点和 Prompt。
- 输出符合字段规范的 JSON。

交付物：

- 已发布 workflow。
- Dify 输入变量清单。
- Dify 输出 JSON 示例。
- workflow 版本说明。

### 5.3 阶段三：真实 API 联调

目标：

- adapter 调用真实 Dify Workflow API。
- 校验 blocking 模式。
- 保留 run id 或 trace。
- 失败时给出明确错误或 fallback 标记。

交付物：

- 远端 Dify adapter 接入。
- mocked HTTP 测试。
- 真实联调记录。

### 5.4 阶段四：稳定运行

目标：

- 明确 API Key 管理。
- 明确超时、重试和错误归档。
- 明确 Dify workflow 变更时的回归测试。

交付物：

- 运行配置说明。
- 验收记录。
- 版本变更记录。

## 6. 新增 Dify 组织器流程

新增一个 Dify 型组织器时，应按以下顺序执行：

1. 确定组织器目标和差异策略。
2. 编写或更新专项搭建规范。
3. 新增插件目录和 manifest。
4. 编写本地 Dify-shaped `workflow.json`。
5. 编写 adapter 与测试。
6. 在 Dify 工作台按专项规范搭建 workflow。
7. 联调真实 API。
8. 回写联调结果和变更说明。

## 7. API Key 与安全

真实密钥不得写入：

- Git 仓库。
- 文档正文。
- 测试快照。
- 前端代码。

应通过环境变量或部署密钥系统注入。测试只能使用占位值，例如 `test-dify-key`。

## 8. 验收标准

Dify 型组织器完成协作闭环，至少满足：

- 正式文档中有公共合同、Dify 字段规范和专项搭建规范。
- 插件目录可被发现。
- 页面可选择该组织器。
- 本地 fallback 或本地 Dify-shaped workflow 测试通过。
- 真实 Dify workflow 已发布。
- adapter 能调用真实 API 并处理成功、失败、超时和结构错误。
- 输出能进入 `P2` 页面、临时正文、状态区和过程区。
