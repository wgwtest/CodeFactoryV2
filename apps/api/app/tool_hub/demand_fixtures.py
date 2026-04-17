from __future__ import annotations

from app.tool_hub.models import ComponentSpec, ToolDemandNode, ToolDemandSheetCreateRequest, ToolDemandSource


def build_mock_demand_request(scenario_id: str) -> ToolDemandSheetCreateRequest:
    builders = {
        "simulated_blue_force": build_mock_blue_force_request,
        "navigation_planning": build_mock_navigation_planning_request,
        "data_governance": build_mock_data_governance_request,
    }
    builder = builders.get(scenario_id)
    if builder is None:
        raise ValueError(f"Unsupported mock demand scenario: {scenario_id}")
    return builder()


def build_mock_blue_force_request() -> ToolDemandSheetCreateRequest:
    return ToolDemandSheetCreateRequest(
        sheet_name="模拟蓝军一期工具需求单",
        source=ToolDemandSource(
            phase="p3_simulator",
            producer="mock_blue_force_generator",
            business_case="simulated_blue_force",
            scenario_id="blue-force-sim-001",
            scenario_name="模拟蓝军对抗推演一期",
        ),
        requested_by="P3",
        notes="当前阶段为 P4 输入工序链最小闭环验证单。",
        root_node=_build_root_node(
            node_id="sys-blue-force",
            node_name="模拟蓝军系统",
            node_code="SYS-BLUE-FORCE",
            business_domain_id="simulated_blue_force",
            subsystems=[
                _build_subsystem_node(
                    node_id="subsys-battlefield-modeling",
                    node_name="战场建模",
                    node_code="SUBSYS-BATTLEFIELD-MODELING",
                    business_domain_id="simulated_blue_force",
                    child=_build_sub_subsystem_node(
                        node_id="subsub-spatial-environment-modeling",
                        node_name="空间环境建模",
                        node_code="SUBSUB-SPATIAL-ENVIRONMENT-MODELING",
                        business_domain_id="simulated_blue_force",
                        modules=[
                            _build_module_node(
                                node_id="module-terrain-modeling",
                                node_name="地图地形建模",
                                node_code="MODULE-TERRAIN-MODELING",
                                business_domain_id="simulated_blue_force",
                                component=_build_component_node(
                                    node_id="component-battlefield-basemap-importer",
                                    node_name="战场底图导入器",
                                    node_code="COMP-BATTLEFIELD-BASEMAP-IMPORTER",
                                    business_domain_id="simulated_blue_force",
                                    problem_statement="导入战场底图并形成可复用地图数据。",
                                    input_types=["map_asset"],
                                    output_types=["battlefield_map"],
                                    keywords=["战场", "底图", "导入"],
                                ),
                            ),
                            _build_module_node(
                                node_id="module-visibility-analysis",
                                node_name="环境条件建模",
                                node_code="MODULE-VISIBILITY-ANALYSIS",
                                business_domain_id="simulated_blue_force",
                                component=_build_component_node(
                                    node_id="component-line-of-sight-analyzer",
                                    node_name="通视遮蔽分析器",
                                    node_code="COMP-LINE-OF-SIGHT-ANALYZER",
                                    business_domain_id="simulated_blue_force",
                                    problem_statement="分析地形与障碍对通视关系的影响。",
                                    input_types=["terrain_layer"],
                                    output_types=["visibility_report"],
                                    keywords=["通视", "遮蔽", "分析"],
                                ),
                            ),
                        ],
                    ),
                ),
                _build_subsystem_node(
                    node_id="subsys-blue-force-organization",
                    node_name="蓝军编组",
                    node_code="SUBSYS-BLUE-FORCE-ORGANIZATION",
                    business_domain_id="simulated_blue_force",
                    child=_build_sub_subsystem_node(
                        node_id="subsub-force-structure",
                        node_name="兵力结构编组",
                        node_code="SUBSUB-FORCE-STRUCTURE",
                        business_domain_id="simulated_blue_force",
                        modules=[
                            _build_module_node(
                                node_id="module-force-tree-generation",
                                node_name="编制树生成",
                                node_code="MODULE-FORCE-TREE-GENERATION",
                                business_domain_id="simulated_blue_force",
                                component=_build_component_node(
                                    node_id="component-blue-force-tree-builder",
                                    node_name="蓝军编组树构造器",
                                    node_code="COMP-BLUE-FORCE-TREE-BUILDER",
                                    business_domain_id="simulated_blue_force",
                                    problem_statement="基于兵力定义生成蓝军编组树。",
                                    input_types=["force_definition"],
                                    output_types=["force_tree"],
                                    keywords=["蓝军", "编组", "树"],
                                ),
                            )
                        ],
                    ),
                ),
                _build_subsystem_node(
                    node_id="subsys-wargame",
                    node_name="对抗推演",
                    node_code="SUBSYS-WARGAME",
                    business_domain_id="simulated_blue_force",
                    child=_build_sub_subsystem_node(
                        node_id="subsub-rule-engine",
                        node_name="推演规则驱动",
                        node_code="SUBSUB-RULE-ENGINE",
                        business_domain_id="simulated_blue_force",
                        modules=[
                            _build_module_node(
                                node_id="module-rule-set-assembly",
                                node_name="规则集装配",
                                node_code="MODULE-RULE-SET-ASSEMBLY",
                                business_domain_id="simulated_blue_force",
                                component=_build_component_node(
                                    node_id="component-engagement-rule-assembler",
                                    node_name="交战规则装配器",
                                    node_code="COMP-ENGAGEMENT-RULE-ASSEMBLER",
                                    business_domain_id="simulated_blue_force",
                                    problem_statement="装配推演所需的交战规则集。",
                                    input_types=["rule_definition"],
                                    output_types=["rule_bundle"],
                                    keywords=["交战", "规则", "装配"],
                                ),
                            )
                        ],
                    ),
                ),
                _build_subsystem_node(
                    node_id="subsys-action-control",
                    node_name="行动控制",
                    node_code="SUBSYS-ACTION-CONTROL",
                    business_domain_id="simulated_blue_force",
                    child=_build_sub_subsystem_node(
                        node_id="subsub-mission-control",
                        node_name="任务下达控制",
                        node_code="SUBSUB-MISSION-CONTROL",
                        business_domain_id="simulated_blue_force",
                        modules=[
                            _build_module_node(
                                node_id="module-action-plan-orchestration",
                                node_name="行动计划编排",
                                node_code="MODULE-ACTION-PLAN-ORCHESTRATION",
                                business_domain_id="simulated_blue_force",
                                component=_build_component_node(
                                    node_id="component-action-plan-orchestrator",
                                    node_name="行动计划编排器",
                                    node_code="COMP-ACTION-PLAN-ORCHESTRATOR",
                                    business_domain_id="simulated_blue_force",
                                    problem_statement="编排行动任务和时间序列控制计划。",
                                    input_types=["mission_definition"],
                                    output_types=["action_plan"],
                                    keywords=["行动", "计划", "编排"],
                                ),
                            )
                        ],
                    ),
                ),
                _build_subsystem_node(
                    node_id="subsys-assessment-review",
                    node_name="评估复盘",
                    node_code="SUBSYS-ASSESSMENT-REVIEW",
                    business_domain_id="simulated_blue_force",
                    child=_build_sub_subsystem_node(
                        node_id="subsub-result-assessment",
                        node_name="结果评估",
                        node_code="SUBSUB-RESULT-ASSESSMENT",
                        business_domain_id="simulated_blue_force",
                        modules=[
                            _build_module_node(
                                node_id="module-effect-metrics",
                                node_name="指标评估",
                                node_code="MODULE-EFFECT-METRICS",
                                business_domain_id="simulated_blue_force",
                                component=_build_component_node(
                                    node_id="component-effect-metrics-calculator",
                                    node_name="效果指标计算器",
                                    node_code="COMP-EFFECT-METRICS-CALCULATOR",
                                    business_domain_id="simulated_blue_force",
                                    problem_statement="计算对抗结果的关键效果指标。",
                                    input_types=["simulation_result"],
                                    output_types=["metric_report"],
                                    keywords=["效果", "指标", "计算"],
                                ),
                            )
                        ],
                    ),
                ),
            ],
        ),
    )


def build_mock_navigation_planning_request() -> ToolDemandSheetCreateRequest:
    return ToolDemandSheetCreateRequest(
        sheet_name="导航规划一期工具需求单",
        source=ToolDemandSource(
            phase="p3_simulator",
            producer="mock_navigation_planning_generator",
            business_case="navigation_planning",
            scenario_id="navigation-planning-sim-001",
            scenario_name="导航规划协同推演一期",
        ),
        requested_by="P3",
        notes="用于验证 P3 端可切换不同业务方向发起工单。",
        root_node=_build_root_node(
            node_id="sys-navigation-planning",
            node_name="导航规划系统",
            node_code="SYS-NAVIGATION-PLANNING",
            business_domain_id="navigation_planning",
            subsystems=[
                _build_subsystem_node(
                    node_id="subsys-route-design",
                    node_name="航路设计",
                    node_code="SUBSYS-ROUTE-DESIGN",
                    business_domain_id="navigation_planning",
                    child=_build_sub_subsystem_node(
                        node_id="subsub-path-planning",
                        node_name="路径规划",
                        node_code="SUBSUB-PATH-PLANNING",
                        business_domain_id="navigation_planning",
                        modules=[
                            _build_module_node(
                                node_id="module-route-assembly",
                                node_name="航路装配",
                                node_code="MODULE-ROUTE-ASSEMBLY",
                                business_domain_id="navigation_planning",
                                component=_build_component_node(
                                    node_id="component-route-plan-compiler",
                                    node_name="航路规划编译器",
                                    node_code="COMP-ROUTE-PLAN-COMPILER",
                                    business_domain_id="navigation_planning",
                                    problem_statement="根据任务区域和约束条件生成可执行航路方案。",
                                    input_types=["manual_text"],
                                    output_types=["structured_json"],
                                    keywords=["导航", "航路", "规划"],
                                ),
                            )
                        ],
                    ),
                ),
                _build_subsystem_node(
                    node_id="subsys-conflict-check",
                    node_name="冲突校核",
                    node_code="SUBSYS-CONFLICT-CHECK",
                    business_domain_id="navigation_planning",
                    child=_build_sub_subsystem_node(
                        node_id="subsub-airspace-rules",
                        node_name="空域约束检查",
                        node_code="SUBSUB-AIRSPACE-RULES",
                        business_domain_id="navigation_planning",
                        modules=[
                            _build_module_node(
                                node_id="module-conflict-analysis",
                                node_name="冲突分析",
                                node_code="MODULE-CONFLICT-ANALYSIS",
                                business_domain_id="navigation_planning",
                                component=_build_component_node(
                                    node_id="component-conflict-window-analyzer",
                                    node_name="冲突窗口分析器",
                                    node_code="COMP-CONFLICT-WINDOW-ANALYZER",
                                    business_domain_id="navigation_planning",
                                    problem_statement="分析航路与时空约束冲突窗口。",
                                    input_types=["manual_text"],
                                    output_types=["review_suggestion"],
                                    keywords=["冲突", "空域", "校核"],
                                ),
                            )
                        ],
                    ),
                ),
            ],
        ),
    )


def build_mock_data_governance_request() -> ToolDemandSheetCreateRequest:
    return ToolDemandSheetCreateRequest(
        sheet_name="数据治理一期工具需求单",
        source=ToolDemandSource(
            phase="p3_simulator",
            producer="mock_data_governance_generator",
            business_case="data_governance",
            scenario_id="data-governance-sim-001",
            scenario_name="数据治理质量提升一期",
        ),
        requested_by="P3",
        notes="用于验证数据治理类典型工单的输入闭环。",
        root_node=_build_root_node(
            node_id="sys-data-governance",
            node_name="数据治理系统",
            node_code="SYS-DATA-GOVERNANCE",
            business_domain_id="data_governance",
            subsystems=[
                _build_subsystem_node(
                    node_id="subsys-quality-check",
                    node_name="质量校核",
                    node_code="SUBSYS-QUALITY-CHECK",
                    business_domain_id="data_governance",
                    child=_build_sub_subsystem_node(
                        node_id="subsub-entity-standardization",
                        node_name="对象标准化",
                        node_code="SUBSUB-ENTITY-STANDARDIZATION",
                        business_domain_id="data_governance",
                        modules=[
                            _build_module_node(
                                node_id="module-duplicate-detection",
                                node_name="重复识别",
                                node_code="MODULE-DUPLICATE-DETECTION",
                                business_domain_id="data_governance",
                                component=_build_component_node(
                                    node_id="component-entity-duplicate-inspector",
                                    node_name="对象重复检测器",
                                    node_code="COMP-ENTITY-DUPLICATE-INSPECTOR",
                                    business_domain_id="data_governance",
                                    problem_statement="识别对象清单中的重复项和归并候选。",
                                    input_types=["entity_list"],
                                    output_types=["review_suggestion"],
                                    keywords=["数据治理", "重复", "归并"],
                                ),
                            )
                        ],
                    ),
                ),
                _build_subsystem_node(
                    node_id="subsys-lineage-review",
                    node_name="血缘审查",
                    node_code="SUBSYS-LINEAGE-REVIEW",
                    business_domain_id="data_governance",
                    child=_build_sub_subsystem_node(
                        node_id="subsub-attribute-trace",
                        node_name="字段追踪",
                        node_code="SUBSUB-ATTRIBUTE-TRACE",
                        business_domain_id="data_governance",
                        modules=[
                            _build_module_node(
                                node_id="module-lineage-reporting",
                                node_name="链路核验",
                                node_code="MODULE-LINEAGE-REPORTING",
                                business_domain_id="data_governance",
                                component=_build_component_node(
                                    node_id="component-lineage-gap-reporter",
                                    node_name="血缘缺口报告器",
                                    node_code="COMP-LINEAGE-GAP-REPORTER",
                                    business_domain_id="data_governance",
                                    problem_statement="输出血缘断点与缺失字段的核验报告。",
                                    input_types=["snapshot_json"],
                                    output_types=["validation_report"],
                                    keywords=["血缘", "字段", "核验"],
                                ),
                            )
                        ],
                    ),
                ),
            ],
        ),
    )


def _build_root_node(
    *,
    node_id: str,
    node_name: str,
    node_code: str,
    business_domain_id: str,
    subsystems: list[ToolDemandNode],
) -> ToolDemandNode:
    return ToolDemandNode(
        node_id=node_id,
        node_type="system",
        node_name=node_name,
        node_code=node_code,
        business_domain_id=business_domain_id,
        children=subsystems,
    )


def _build_subsystem_node(
    *,
    node_id: str,
    node_name: str,
    node_code: str,
    business_domain_id: str,
    child: ToolDemandNode,
) -> ToolDemandNode:
    return ToolDemandNode(
        node_id=node_id,
        node_type="subsystem",
        node_name=node_name,
        node_code=node_code,
        business_domain_id=business_domain_id,
        children=[child],
    )


def _build_sub_subsystem_node(
    *,
    node_id: str,
    node_name: str,
    node_code: str,
    business_domain_id: str,
    modules: list[ToolDemandNode],
) -> ToolDemandNode:
    return ToolDemandNode(
        node_id=node_id,
        node_type="sub_subsystem",
        node_name=node_name,
        node_code=node_code,
        business_domain_id=business_domain_id,
        children=modules,
    )


def _build_module_node(
    *,
    node_id: str,
    node_name: str,
    node_code: str,
    business_domain_id: str,
    component: ToolDemandNode,
) -> ToolDemandNode:
    return ToolDemandNode(
        node_id=node_id,
        node_type="module",
        node_name=node_name,
        node_code=node_code,
        business_domain_id=business_domain_id,
        children=[component],
    )


def _build_component_node(
    *,
    node_id: str,
    node_name: str,
    node_code: str,
    business_domain_id: str,
    problem_statement: str,
    input_types: list[str],
    output_types: list[str],
    keywords: list[str],
) -> ToolDemandNode:
    return ToolDemandNode(
        node_id=node_id,
        node_type="component",
        node_name=node_name,
        node_code=node_code,
        business_domain_id=business_domain_id,
        children=[],
        component_spec=ComponentSpec(
            component_name=node_name,
            component_code=node_code,
            problem_statement=problem_statement,
            required_input_types=input_types,
            expected_output_types=output_types,
            preferred_tool_forms=["skill"],
            preferred_runtime_platforms=["agent_runtime"],
            lifecycle_stage_ids=["solution_design"],
            keywords=keywords,
            acceptance_notes=f"{node_name} 输出需可被 P5-sim 查询验证。",
        ),
    )
