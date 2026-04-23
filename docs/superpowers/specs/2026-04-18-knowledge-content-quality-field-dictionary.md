# 知识内容质量字段字典

## 文档目的

本文件用于定义知识内容质量标准中的字段清单，并明确每个字段的：

1. 概念
2. 含义
3. 数据类型
4. 取值范围
5. 字段不满足时代表的质量问题

本文件不讨论具体代码实现，不规定某个字段必须立即启用，仅作为后续策略配置、页面展示和评估解释的统一语义基础。

## 字段分层

本字典只包含三类字段：

1. 知识项级字段
2. 关系级字段
3. 发布批次级字段

## 一、知识项级字段

### 1. 标识与命名质量

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `item.item_type_valid` | 知识类型合法性 | 该知识项是否属于允许的知识类型集合 | `boolean` | `true/false` | 仅判断类型是否合法，不判断内容质量高低 |
| `item.canonical_name_present` | 标准名称存在性 | 是否存在明确的标准名称 | `boolean` | `true/false` | 缺失时说明知识对象不可识别 |
| `item.canonical_name_length_min` | 标准名称最小长度 | 标准名称至少应达到的长度 | `integer` | `1-255` | 用于避免过短、无意义名称 |
| `item.canonical_name_length_max` | 标准名称最大长度 | 标准名称允许的最大长度 | `integer` | `1-512` | 用于避免句子化、段落化名称 |
| `item.canonical_name_noise_free` | 标准名称去噪 | 标准名称是否不含明显噪声、编号串、模板残片 | `boolean` | `true/false` | 失败通常说明抽取到了脏文本 |
| `item.canonical_name_not_sentence_fragment` | 标准名称非句子片段 | 标准名称是否不是自然语言句子或定义片段 | `boolean` | `true/false` | 失败通常说明应进入治理而非直接入库 |
| `item.canonical_name_not_code_like` | 标准名称非编码串 | 标准名称是否不是部队代号、编号串、模板码等 | `boolean` | `true/false` | 失败时通常应拒绝或人工复核 |
| `item.canonical_name_specificity_level` | 标准名称具体度 | 名称是否足够具体，避免“计划”“系统”“模块”这类过泛命名 | `enum` | `high`、`medium`、`low` | 适合做评分或人工复核触发 |
| `item.canonical_name_uniqueness_scope` | 标准名称唯一性范围 | 名称在当前知识库内是否与其他项形成高冲突 | `enum` | `unique`、`near_duplicate`、`ambiguous` | 用于判断是否允许自动入库 |

### 2. 类别与归类质量

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `item.category_present` | 类别存在性 | 知识项是否有明确类别 | `boolean` | `true/false` | 无类别通常不能直接进入发布态 |
| `item.category_in_controlled_vocabulary` | 类别受控词表命中 | 类别是否命中项目定义的受控词表 | `boolean` | `true/false` | 不命中时说明分类体系不稳定 |
| `item.category_conflict_count_max` | 类别冲突上限 | 同一知识项允许出现的类别冲突数量上限 | `integer` | `0-99` | 通常用于限制跨文档归并时的类别漂移 |
| `item.taxonomy_position_clear` | 分类位置清晰 | 知识项在分类体系中的位置是否明确 | `boolean` | `true/false` | 适合控制模糊挂类、混合挂类问题 |

### 3. 定义与语义清晰度

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `item.definition_present` | 定义存在性 | 知识项是否具有可解释的定义描述 | `boolean` | `true/false` | 没有定义时仍可进入工作态，但发布通常应更严格 |
| `item.definition_min_length` | 定义最小长度 | 定义文本最小长度 | `integer` | `0-5000` | 用于避免定义过短、无信息量 |
| `item.definition_clarity_level` | 定义清晰度 | 定义是否足够清楚、非模糊、非残句 | `enum` | `high`、`medium`、`low` | 建议作为人工复核优先级参考 |
| `item.definition_not_circular` | 定义非循环性 | 定义不能只是同义反复或名称重复解释 | `boolean` | `true/false` | 例如“空域协同平台是一个空域协同平台”应判失败 |
| `item.definition_scope_consistent` | 定义范围一致性 | 定义描述的范围是否与类别、名称保持一致 | `boolean` | `true/false` | 防止实体名配了流程定义、流程名配了组织定义 |

### 4. 别名与归一质量

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `item.aliases_count_max` | 别名数量上限 | 单个知识项允许的最大别名数量 | `integer` | `0-200` | 用于防止归并时把噪声都收进来 |
| `item.aliases_noise_ratio_max` | 别名噪声占比上限 | 别名集合中允许出现的噪声比例上限 | `float` | `0.0-1.0` | 例如 0.2 表示最多 20% 别名可疑 |
| `item.aliases_deduplicated` | 别名去重完成 | 别名集合是否已去重 | `boolean` | `true/false` | 基础一致性字段 |
| `item.aliases_semantically_consistent` | 别名语义一致 | 别名是否都指向同一知识对象 | `boolean` | `true/false` | 防止错误合并导致“一个项包含多义别名” |

### 5. 证据质量

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `item.evidence_required` | 证据必需性 | 知识项是否必须有证据才允许入库 | `boolean` | `true/false` | 内容质量中的核心字段之一 |
| `item.evidence_count_min` | 最少证据条数 | 单个知识项最少需要多少条证据 | `integer` | `0-100` | 可按知识库调整严格程度 |
| `item.evidence_excerpt_min_length` | 单条证据最小长度 | 单条证据片段最小长度 | `integer` | `0-2000` | 防止只截一个词或半个短语 |
| `item.evidence_anchor_required` | 证据定位锚点必需 | 证据是否必须带可定位锚点 | `boolean` | `true/false` | 锚点可以是页码、段落或 chunk 引用 |
| `item.evidence_traceable_to_document` | 证据可追溯到文档 | 证据是否必须明确指向来源文档 | `boolean` | `true/false` | 这是可追溯性的硬基础 |
| `item.evidence_traceable_to_location` | 证据可追溯到位置 | 证据是否必须落到文档中的具体位置 | `boolean` | `true/false` | 比“可追到文档”更严格 |
| `item.evidence_supports_name` | 证据支撑名称 | 证据是否能够直接支撑知识项命名 | `boolean` | `true/false` | 防止名字是臆造、证据只支撑上下文 |
| `item.evidence_supports_category` | 证据支撑类别 | 证据是否足以支撑该项被归入当前类别 | `boolean` | `true/false` | 常用于防止误分类 |
| `item.evidence_supports_definition` | 证据支撑定义 | 证据是否足以支撑定义文本而非只支撑名称 | `boolean` | `true/false` | 用于更高质量发布门槛 |
| `item.contradictory_evidence_allowed` | 允许矛盾证据 | 是否允许同一知识项带有互相冲突的证据 | `boolean` | `true/false` | 通常允许存在，但应触发人工复核 |

### 6. 来源支撑质量

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `item.supporting_document_count_min` | 最少支撑文档数 | 单个知识项至少需要多少份文档支持 | `integer` | `0-100` | 适合区分探索态与发布态 |
| `item.supporting_source_group_count_min` | 最少来源组数 | 至少需要多少类来源组支撑 | `integer` | `0-50` | 来源组可按材料目录、文献族、渠道划分 |
| `item.single_document_entry_allowed` | 允许单文档入库 | 是否允许仅单文档支持就进入工作态或发布态 | `boolean` | `true/false` | 很关键的策略开关 |
| `item.cross_document_support_required` | 需要跨文档支撑 | 是否要求必须跨文档支撑 | `boolean` | `true/false` | 常用于高置信度发布 |
| `item.cross_source_support_required` | 需要跨来源支撑 | 是否要求必须跨来源组支撑 | `boolean` | `true/false` | 对抗单一来源偏差 |
| `item.source_diversity_min` | 最小来源多样性 | 支撑来源的最小多样性指标 | `float` | `0.0-1.0` | 可由来源组覆盖率或分布均衡度计算 |
| `item.source_conflict_count_max` | 来源冲突上限 | 允许出现的来源冲突数上限 | `integer` | `0-100` | 用于控制多文档归并中的矛盾 |
| `item.source_consistency_required` | 来源一致性要求 | 来源之间对该项描述是否必须基本一致 | `boolean` | `true/false` | 可用于控制发布前收敛程度 |

### 7. 语义一致性与歧义控制

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `item.duplicate_candidate_count_max` | 重复候选上限 | 同一知识项允许存在的高相似候选数量上限 | `integer` | `0-999` | 用于衡量归并是否足够干净 |
| `item.same_name_multi_category_allowed` | 同名多类允许性 | 同一名称是否允许出现在多个类别中 | `boolean` | `true/false` | 对语义歧义非常关键 |
| `item.alias_collision_allowed` | 别名冲突允许性 | 一个别名是否允许指向多个知识项 | `boolean` | `true/false` | 一般应谨慎放开 |
| `item.semantic_scope_clear` | 语义范围清晰 | 知识项边界是否清楚，不与上下位概念混叠 | `boolean` | `true/false` | 适合在治理态显式展示 |
| `item.granularity_consistent` | 粒度一致性 | 知识项是否与当前分类层级保持一致粒度 | `boolean` | `true/false` | 防止“系统”和“子功能”混作同层项 |
| `item.item_distinguishable_from_near_duplicates` | 可与近重复项区分 | 当前项是否能与相近项明确区分 | `boolean` | `true/false` | 不满足时通常应合并或人工复核 |
| `item.manual_review_required_for_ambiguous_item` | 歧义项需人工复核 | 当存在歧义时是否强制人工复核 | `boolean` | `true/false` | 这是治理门槛而不是内容本身 |

## 二、关系级字段

### 1. 关系合法性

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `relation.relation_type_valid` | 关系类型合法性 | 关系类型是否属于允许集合 | `boolean` | `true/false` | 基础准入字段 |
| `relation.relation_type_in_controlled_vocabulary` | 关系词表命中 | 关系类型是否命中受控关系词表 | `boolean` | `true/false` | 用于防止自造关系名 |

### 2. 端点正确性

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `relation.endpoints_exist` | 端点存在性 | 关系两端的知识项是否都存在 | `boolean` | `true/false` | 图谱关系的基本要求 |
| `relation.endpoints_type_compatible` | 端点类型兼容性 | 两端点类型是否满足当前关系的语义约束 | `boolean` | `true/false` | 例如流程不能被当作文档去描述 |
| `relation.endpoints_category_compatible` | 端点类别兼容性 | 两端点类别组合是否合理 | `boolean` | `true/false` | 更细粒度的约束 |
| `relation.direction_valid` | 方向合法性 | 关系方向是否符合定义 | `boolean` | `true/false` | 常用于 `part_of`、`describes` 等方向性关系 |

### 3. 关系证据质量

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `relation.evidence_required` | 关系证据必需性 | 关系是否必须附带证据 | `boolean` | `true/false` | 建议默认开启 |
| `relation.evidence_count_min` | 关系最少证据条数 | 每条关系所需的最少证据条数 | `integer` | `0-100` | 比知识项更严格时也合理 |
| `relation.evidence_anchor_required` | 关系证据锚点必需 | 关系证据是否必须带定位锚点 | `boolean` | `true/false` | 方便后续解释关系如何成立 |
| `relation.evidence_supports_both_endpoints` | 证据同时支撑两端 | 证据是否必须同时指向关系的两端及其关系语义 | `boolean` | `true/false` | 避免关系由弱共现误判生成 |

### 4. 关系支撑广度

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `relation.supporting_document_count_min` | 关系最少支撑文档数 | 一条关系至少需要多少份文档支持 | `integer` | `0-100` | 可区分探索图谱与正式图谱 |
| `relation.cross_source_support_required` | 关系跨来源支撑要求 | 是否要求关系至少得到多个来源组支持 | `boolean` | `true/false` | 用于提高正式发布质量 |
| `relation.confidence_min` | 关系最小置信度 | 关系允许进入工作态或发布态的最小置信度 | `float` | `0.0-1.0` | 仍属于内容质量，不属于模型选择 |

### 5. 图结构合理性

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `relation.self_loop_allowed` | 允许自环 | 是否允许关系起点和终点是同一知识项 | `boolean` | `true/false` | 某些图模型可允许，大多数业务图谱应限制 |
| `relation.duplicate_relation_count_max` | 重复关系上限 | 同类型同端点的重复关系允许上限 | `integer` | `0-999` | 防止图谱膨胀和重复写入 |
| `relation.orphan_relation_allowed` | 允许孤立关系 | 是否允许端点不在当前可见图谱中的关系存在 | `boolean` | `true/false` | 发布态通常应严格限制 |
| `relation.contradictory_relation_allowed` | 允许矛盾关系 | 是否允许同一对端点存在语义矛盾关系 | `boolean` | `true/false` | 若允许，应强制人工审查 |
| `relation.manual_review_required_for_cross_category_relation` | 跨类别关系需人工复核 | 高风险跨类别关系是否必须人工审查 | `boolean` | `true/false` | 适合治理态策略 |

## 三、发布批次级字段

### 1. 审核完成度

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `publication.approved_only` | 仅发布已批准项 | 发布时是否只允许已批准知识项进入正式版本 | `boolean` | `true/false` | 当前系统已有类似语义 |
| `publication.review_status_required` | 审核状态必需 | 所有待发布项是否都必须具有审核状态 | `boolean` | `true/false` | 用于避免无状态项混入 |
| `publication.review_completion_ratio_min` | 最小审核完成率 | 当前发布批次中完成审核的项占比最低要求 | `float` | `0.0-1.0` | 例如 1.0 表示必须全部审完 |
| `publication.unreviewed_item_count_max` | 未审项上限 | 发布前允许保留的未审项数量上限 | `integer` | `0-999999` | 与审核完成率互补 |

### 2. 批次结构完整性

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `publication.approved_item_count_min` | 最少已批准知识项数 | 发布批次至少要包含多少已批准知识项 | `integer` | `0-999999` | 防止空发布或样本过小 |
| `publication.approved_entity_count_min` | 最少已批准实体数 | 发布批次中实体最少数量 | `integer` | `0-999999` | 用于控制结构完整性 |
| `publication.approved_event_count_min` | 最少已批准事件数 | 发布批次中事件最少数量 | `integer` | `0-999999` | 可按业务需要设为 0 |
| `publication.approved_process_count_min` | 最少已批准流程数 | 发布批次中流程最少数量 | `integer` | `0-999999` | 对流程导向库很重要 |
| `publication.approved_relation_count_min` | 最少已批准关系数 | 发布批次中关系最少数量 | `integer` | `0-999999` | 用于控制图谱稀疏度 |

### 3. 批次证据覆盖率

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `publication.evidence_coverage_ratio_min` | 最小证据覆盖率 | 已发布项中带证据的比例最低要求 | `float` | `0.0-1.0` | 是批次级质量核心指标 |
| `publication.anchored_evidence_ratio_min` | 最小锚点证据覆盖率 | 已发布项中带锚点证据的比例最低要求 | `float` | `0.0-1.0` | 用于保证可追溯质量 |
| `publication.definition_coverage_ratio_min` | 最小定义覆盖率 | 已发布项中具有定义的比例最低要求 | `float` | `0.0-1.0` | 用于提升最终可用性 |
| `publication.multi_source_support_ratio_min` | 最小多来源支撑覆盖率 | 已发布项中得到多来源支撑的比例最低要求 | `float` | `0.0-1.0` | 对高可信发布很重要 |

### 4. 低质量项占比控制

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `publication.low_confidence_item_ratio_max` | 低置信度项占比上限 | 批次中低于置信度阈值的知识项占比上限 | `float` | `0.0-1.0` | 越低说明发布越严格 |
| `publication.low_confidence_relation_ratio_max` | 低置信度关系占比上限 | 批次中低于置信度阈值的关系占比上限 | `float` | `0.0-1.0` | 图谱型知识库应重点关注 |
| `publication.missing_definition_item_ratio_max` | 缺定义项占比上限 | 缺少定义的知识项占比上限 | `float` | `0.0-1.0` | 适合控制“只有名字没有解释” |
| `publication.missing_traceability_item_ratio_max` | 缺可追溯项占比上限 | 缺少可追溯证据链的知识项占比上限 | `float` | `0.0-1.0` | 与证据覆盖率不同，更强调链路完整 |

### 5. 冲突和残缺项控制

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `publication.unresolved_conflict_count_max` | 未解决冲突上限 | 发布前允许保留的未解决冲突总数上限 | `integer` | `0-999999` | 冲突可来自名称、类别、关系等 |
| `publication.rejected_conflict_count_max` | 驳回冲突项上限 | 与已发布内容直接冲突的驳回项允许上限 | `integer` | `0-999999` | 常用于严格发布门槛 |
| `publication.orphan_item_ratio_max` | 孤立知识项占比上限 | 没有被任何关系连接的知识项占比上限 | `float` | `0.0-1.0` | 并非所有知识库都需要严格限制 |
| `publication.orphan_relation_ratio_max` | 孤立关系占比上限 | 无法构成有效结构的关系占比上限 | `float` | `0.0-1.0` | 用于控制图谱异常边 |
| `publication.duplicate_cluster_count_max` | 重复簇上限 | 未完成去重或合并的重复知识簇数量上限 | `integer` | `0-999999` | 用于衡量治理是否收敛 |

### 6. 发布治理要求

| 字段键 | 概念 | 含义 | 数据类型 | 取值范围 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `publication.publication_diff_review_required` | 发布差异复核必需 | 发布前是否必须审阅工作态与发布态差异 | `boolean` | `true/false` | 属于发布治理动作要求 |
| `publication.publication_rationale_required` | 发布说明必需 | 发布时是否必须填写版本说明或发布依据 | `boolean` | `true/false` | 对审计和回溯很重要 |

## 四、字段使用建议

### 1. 不要把所有字段都当成“硬拦截”

字段定义完整，不代表所有字段都应一开始就作为发布阻断条件。建议按使用强度分层：

1. 硬阻断字段
2. 人工复核字段
3. 告警字段

### 2. 不要一开始就追求阈值完美

当前阶段应先建立字段语义，再通过真实知识库使用反馈逐步修订阈值。

### 3. 字段应允许按知识库覆盖

同一字段在不同知识库中的默认值可以不同，但字段语义本身应保持统一。

## 五、后续建议

本字典完成后，下一步建议继续梳理：

1. 哪些字段属于硬底线
2. 哪些字段适合形成默认模板
3. 哪些字段应允许按知识库单独覆盖
4. 哪些字段更适合作为人工复核触发器而非直接拦截项
