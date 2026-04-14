# OpenAI 兼容 LLM 适配模块设计

## 背景

当前知识抽取链路已经具备以下基本形态：

`文档解析 -> 规则/schema 抽取 -> LLM 结构化抽取增强 -> 候选知识融合 -> 建库/治理/展示`

在这条链路中，`LlamaIndex` 承担的是结构化抽取编排职责，不是模型本身。真实的模型调用由底层 LLM 提供方完成。

本轮验证发现一个明确问题：

1. `DeepSeek` 提供了标准的 OpenAI 兼容 API。
2. 直接按 OpenAI 兼容协议调用 `DeepSeek` 是可行的。
3. 但 `LlamaIndex` 自带的 `OpenAI` 适配器会校验模型名，并依赖内部 OpenAI 模型白名单。
4. 因此，`deepseek-chat` 这类第三方模型虽然协议兼容，但不能被当前适配器直接接受。

这说明问题不在于 `DeepSeek` 不兼容，而在于当前工程缺少一个“**面向 OpenAI 兼容接口的模型适配层**”。

如果不把这层独立抽出来，后续每接一个兼容供应商，都要在知识抽取代码里写临时判断，最终会造成：

1. 抽取服务与模型供应商耦合。
2. 配置项越来越散。
3. 供应商切换要改业务逻辑。
4. 兼容性问题无法被单独测试和沉淀。

因此，这个模块应被单独设计为一个可复用的基础能力。

## 设计目标

本模块的目标不是“再封一层调用代码”，而是把“**OpenAI 兼容协议接入**”抽象成平台级基础能力。

具体目标如下：

1. 支持用统一方式接入 `OpenAI`、`DeepSeek` 及其他 OpenAI 兼容供应商。
2. 屏蔽 `LlamaIndex OpenAI` 适配器对官方模型白名单的依赖。
3. 向上层暴露稳定的结构化抽取能力，而不是暴露供应商差异。
4. 保持当前知识抽取主链路不变，只替换 LLM 接入层。
5. 允许后续在软件生成、组件生成、问答检索等其他模块中复用同一适配能力。

## 非目标

本模块本轮不负责以下内容：

1. 不负责文档解析。
2. 不负责知识 schema 设计。
3. 不负责供应商 SDK 全量封装。
4. 不负责向量检索、Agent、多轮会话等高级编排。
5. 不负责供应商计费、配额管理和运营级监控。

## 模块定位

该模块定位为：

`结构化 LLM 访问适配层`

它位于：

- 上游：`ExtractionService`、未来的软件生成服务、组件生成服务
- 下游：`LlamaIndex`、OpenAI 兼容 HTTP API、供应商模型服务

它的责任边界应严格限定为：

1. 接收统一配置。
2. 构造兼容的 LLM 客户端。
3. 对外提供统一的结构化输出调用能力。
4. 处理模型元数据、协议兼容差异和基础错误透传。

它不应承担业务 prompt 设计、抽取后处理和领域规则判断。

## 总体设计

### 1. 分层结构

建议将该模块拆成三层：

#### 1.1 Provider 配置层

负责描述当前使用哪个供应商，以及该供应商的连接参数。

建议配置项：

- `provider`: 供应商标识，例如 `openai`、`deepseek`、`openai_compatible`
- `base_url`: API 基地址
- `api_key`: 密钥
- `model`: 模型名
- `temperature`: 推理温度
- `context_window`: 上下文窗口大小
- `supports_function_calling`: 是否支持函数调用/结构化输出
- `supports_chat`: 是否按 chat 模型处理
- `enabled`: 是否启用 LLM 增强

#### 1.2 LLM 适配层

负责把配置转换成可被 `LlamaIndex` 使用的 LLM 对象。

这一层的核心职责是解决：

1. 模型白名单问题。
2. 元数据声明问题。
3. OpenAI 与 OpenAI 兼容供应商之间的细微差异。

建议抽象为：

- `StructuredLLMAdapterFactory`
- `OpenAIProviderAdapter`
- `OpenAICompatibleProviderAdapter`
- `DeepSeekProviderAdapter`

其中 `DeepSeekProviderAdapter` 可以建立在通用 `OpenAICompatibleProviderAdapter` 之上，只覆盖默认值和少量供应商差异。

#### 1.3 结构化调用层

负责向上层暴露统一接口，例如：

```python
invoke_structured(
    prompt: str,
    output_schema: type[BaseModel],
) -> BaseModel
```

这一层只关心：

1. 输入 prompt
2. 输出 schema
3. 返回结构化对象
4. 错误信息标准化

上层业务服务只应该依赖这一层，而不直接依赖供应商 SDK。

## 关键设计点

### 1. 不能把供应商名写死在抽取服务里

当前知识抽取链只是第一个使用者。后续以下模块都会用到相同能力：

1. 领域知识增强抽取
2. 需求结构化分析
3. 构建描述模型生成
4. 组件说明生成
5. 元数据应用生成辅助

因此适配层必须是独立基础模块，而不是 `ExtractionService` 内部私有实现。

### 2. 不能直接依赖 `LlamaIndex OpenAI` 的官方模型判断

这次已验证：

1. `DeepSeek` 接口兼容 OpenAI。
2. 真实阻塞点是 `LlamaIndex` 用模型名推断 `context_window`、`is_chat_model`、`is_function_calling_model`。

因此模块必须支持“**显式声明模型元数据**”，而不是完全依赖 `LlamaIndex` 的内置判断。

建议策略：

1. 提供一个兼容子类或包装器。
2. 覆盖 `metadata`。
3. 由配置提供 `context_window`、`supports_chat`、`supports_function_calling`。

这样可以让任何 OpenAI 兼容模型在接入时不受官方模型白名单限制。

### 3. Provider 默认值应可覆写

以 `DeepSeek` 为例，默认值可定义为：

- `provider = deepseek`
- `base_url = https://api.deepseek.com/v1`
- `model = deepseek-chat`
- `supports_chat = true`
- `supports_function_calling = true`

但这些默认值必须允许被环境配置覆盖，避免将来供应商接口升级后需要改代码。

### 4. 错误必须标准化

适配层至少要把以下错误统一成平台可处理的错误类型：

1. 配置缺失
2. 鉴权失败
3. 网络错误
4. 模型不支持结构化输出
5. 返回内容无法解析为指定 schema

否则上层业务服务会被迫了解每个供应商的异常格式。

## 与现有工程的集成方式

### 当前集成点

当前实际集成点在：

- `apps/api/app/extraction/service.py`

这里已经有：

1. 规则/schema 抽取
2. LLM enrich 入口
3. 抽取结果融合逻辑

适配模块接入后，`ExtractionService` 不应再直接创建 `LlamaIndex OpenAI` 对象，而应改为：

1. 读取统一 provider 配置
2. 调用适配模块工厂获取结构化 LLM
3. 执行结构化抽取
4. 将结果与规则抽取结果合并

### 推荐目录结构

建议新增独立目录：

```text
apps/api/app/integrations/llm/
  config.py
  schema.py
  exceptions.py
  provider_base.py
  openai_provider.py
  openai_compatible_provider.py
  deepseek_provider.py
  service.py
```

说明：

- `integrations/llm` 明确表示这是基础设施接入层
- 不放在 `extraction/` 下，避免被误认为知识抽取专用私有实现
- 后续其他模块可直接复用

## 配置设计

建议配置收敛为统一命名，而不是散落多个布尔字段。

推荐配置项：

- `KW_LLM_ENABLED`
- `KW_LLM_PROVIDER`
- `KW_LLM_BASE_URL`
- `KW_LLM_API_KEY`
- `KW_LLM_MODEL`
- `KW_LLM_TEMPERATURE`
- `KW_LLM_CONTEXT_WINDOW`
- `KW_LLM_SUPPORTS_CHAT`
- `KW_LLM_SUPPORTS_FUNCTION_CALLING`

对于 `DeepSeek`，配置示例：

```env
KW_LLM_ENABLED=true
KW_LLM_PROVIDER=deepseek
KW_LLM_BASE_URL=https://api.deepseek.com/v1
KW_LLM_API_KEY=sk-xxxx
KW_LLM_MODEL=deepseek-chat
KW_LLM_TEMPERATURE=0
KW_LLM_CONTEXT_WINDOW=64000
KW_LLM_SUPPORTS_CHAT=true
KW_LLM_SUPPORTS_FUNCTION_CALLING=true
```

## 运行时行为

模块运行时应遵循以下顺序：

1. 检查 `enabled`
2. 校验 provider 配置完整性
3. 根据 `provider` 选择适配器
4. 创建兼容 LLM 实例
5. 用指定 schema 执行结构化输出
6. 返回结构化对象
7. 出错时返回标准化异常，由上层决定如何处理失败

这里要强调一点：

不同业务链路的失败策略可以不同。

- 对文档调试、局部验证、开发期排查链路，可以按需要保留 graceful fallback
- 对“知识库正式抽取/重建”链路，不允许因为大模型不可用而静默回退到 `规则/schema` 抽取；必须直接失败并暴露明确错误

也就是说，适配层负责给出标准化异常，而是否允许降级，必须由上层业务链路显式决定

## 为什么这个模块具备高复用价值

这个模块的复用价值主要来自三个方面：

### 1. 复用到其他供应商

未来除了 `DeepSeek`，还可能接入：

1. OpenAI
2. 其他国产 OpenAI 兼容平台
3. 企业私有代理网关
4. 内部模型中台

只要协议兼容，这个模块都可以复用。

### 2. 复用到其他业务能力

除了知识抽取，软件工厂后续多个阶段都会用到“结构化 LLM 输出”，例如：

1. 需求结构化
2. 设计方案分解
3. 组件职责归纳
4. 构建描述模型生成
5. 元数据页面生成

这些都可以直接复用适配层，而不需要每个模块各自处理供应商兼容问题。

### 3. 复用到技术演进

将来如果需要：

1. 增加限流
2. 增加重试
3. 增加调用日志
4. 增加成本统计
5. 增加缓存

都应该在这个适配层做，而不是到每个业务模块重复实现。

## 风险与约束

### 1. OpenAI 兼容不等于行为完全一致

虽然协议兼容，但不同供应商在以下方面仍可能有差异：

1. 函数调用格式细节
2. schema 严格遵从程度
3. 最大上下文窗口
4. 超时表现
5. 限流错误码

因此模块必须把“协议兼容”和“行为兼容”分开处理，不能假设所有兼容供应商行为完全一致。

### 2. 模型元数据不能盲猜

当前验证中，`DeepSeek` 之所以能接通，是因为临时显式声明了：

1. `context_window`
2. `is_chat_model`
3. `is_function_calling_model`

正式实现时，这些参数应通过 provider 配置明确声明，而不是硬编码在业务服务里。

### 3. 密钥不能直接写入仓库

设计上应只支持环境变量和部署配置注入，不允许把实际 key 落到代码仓库或测试数据中。

## 测试策略

### 1. 单元测试

覆盖：

1. 不同 provider 配置能正确路由到对应适配器
2. `DeepSeek` 适配器能正确生成兼容元数据
3. 配置缺失时抛出标准化错误
4. 结构化返回能被 schema 正确解析

### 2. 集成测试

覆盖：

1. 使用 mock OpenAI-compatible endpoint 验证普通补全
2. 使用 mock OpenAI-compatible endpoint 验证结构化输出
3. 验证异常透传和 fallback 行为

### 3. 人工验证

在接入真实供应商时，只做小样本验证：

1. 普通补全
2. 结构化输出
3. 业务抽取样例

不应一上来就对全量档案重跑。

## 验收标准

满足以下条件，可认为该模块设计完成且具备实施价值：

1. 能清楚说明模块为何独立存在，而不是塞进知识抽取服务内部。
2. 能支持 `OpenAI` 与 `DeepSeek` 这类 OpenAI 兼容供应商接入。
3. 上层业务只依赖统一结构化调用接口，不依赖具体供应商 SDK。
4. 供应商切换仅影响配置和适配层，不影响知识抽取主逻辑。
5. 结构化输出失败时，上层能够拿到稳定、标准化的失败信息，并按业务链路决策是否允许降级。

## 下一步建议

在该设计文档确认后，再进入实现阶段，顺序建议如下：

1. 先落独立 `integrations/llm` 适配模块
2. 将 `ExtractionService` 切换到统一 provider 接口
3. 用已验证可用的 `DeepSeek` key 做小样本结构化抽取验证
4. 再处理 `Docling` 的重依赖安装和解析增强问题

这个顺序的原因是：

`LLM 适配问题` 属于抽取增强的“接入问题”，而 `Docling` 属于解析增强的“环境与依赖问题”。

先把接入边界设计和模块化抽出来，后续不论解析器怎么演进，都不会影响 LLM 接入层的复用价值。
