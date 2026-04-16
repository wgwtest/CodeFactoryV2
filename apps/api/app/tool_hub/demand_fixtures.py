from __future__ import annotations

from app.tool_hub.models import ComponentSpec, ToolDemandNode, ToolDemandSheetCreateRequest, ToolDemandSource


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
        root_node=ToolDemandNode(
            node_id="sys-blue-force",
            node_type="system",
            node_name="模拟蓝军系统",
            node_code="SYS-BLUE-FORCE",
            business_domain_id="simulated_blue_force",
            children=[
                _build_subsystem_node(
                    node_id="subsys-battlefield-modeling",
                    node_name="战场建模",
                    node_code="SUBSYS-BATTLEFIELD-MODELING",
                    child=_build_sub_subsystem_node(
                        node_id="subsub-spatial-environment-modeling",
                        node_name="空间环境建模",
                        node_code="SUBSUB-SPATIAL-ENVIRONMENT-MODELING",
                        modules=[
                            _build_module_node(
                                node_id="module-terrain-modeling",
                                node_name="地图地形建模",
                                node_code="MODULE-TERRAIN-MODELING",
                                component=_build_component_node(
                                    node_id="component-battlefield-basemap-importer",
                                    node_name="战场底图导入器",
                                    node_code="COMP-BATTLEFIELD-BASEMAP-IMPORTER",
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
                                component=_build_component_node(
                                    node_id="component-line-of-sight-analyzer",
                                    node_name="通视遮蔽分析器",
                                    node_code="COMP-LINE-OF-SIGHT-ANALYZER",
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
                    child=_build_sub_subsystem_node(
                        node_id="subsub-force-structure",
                        node_name="兵力结构编组",
                        node_code="SUBSUB-FORCE-STRUCTURE",
                        modules=[
                            _build_module_node(
                                node_id="module-force-tree-generation",
                                node_name="编制树生成",
                                node_code="MODULE-FORCE-TREE-GENERATION",
                                component=_build_component_node(
                                    node_id="component-blue-force-tree-builder",
                                    node_name="蓝军编组树构造器",
                                    node_code="COMP-BLUE-FORCE-TREE-BUILDER",
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
                    child=_build_sub_subsystem_node(
                        node_id="subsub-rule-engine",
                        node_name="推演规则驱动",
                        node_code="SUBSUB-RULE-ENGINE",
                        modules=[
                            _build_module_node(
                                node_id="module-rule-set-assembly",
                                node_name="规则集装配",
                                node_code="MODULE-RULE-SET-ASSEMBLY",
                                component=_build_component_node(
                                    node_id="component-engagement-rule-assembler",
                                    node_name="交战规则装配器",
                                    node_code="COMP-ENGAGEMENT-RULE-ASSEMBLER",
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
                    child=_build_sub_subsystem_node(
                        node_id="subsub-mission-control",
                        node_name="任务下达控制",
                        node_code="SUBSUB-MISSION-CONTROL",
                        modules=[
                            _build_module_node(
                                node_id="module-action-plan-orchestration",
                                node_name="行动计划编排",
                                node_code="MODULE-ACTION-PLAN-ORCHESTRATION",
                                component=_build_component_node(
                                    node_id="component-action-plan-orchestrator",
                                    node_name="行动计划编排器",
                                    node_code="COMP-ACTION-PLAN-ORCHESTRATOR",
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
                    child=_build_sub_subsystem_node(
                        node_id="subsub-result-assessment",
                        node_name="结果评估",
                        node_code="SUBSUB-RESULT-ASSESSMENT",
                        modules=[
                            _build_module_node(
                                node_id="module-effect-metrics",
                                node_name="指标评估",
                                node_code="MODULE-EFFECT-METRICS",
                                component=_build_component_node(
                                    node_id="component-effect-metrics-calculator",
                                    node_name="效果指标计算器",
                                    node_code="COMP-EFFECT-METRICS-CALCULATOR",
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


def _build_subsystem_node(
    *,
    node_id: str,
    node_name: str,
    node_code: str,
    child: ToolDemandNode,
) -> ToolDemandNode:
    return ToolDemandNode(
        node_id=node_id,
        node_type="subsystem",
        node_name=node_name,
        node_code=node_code,
        business_domain_id="simulated_blue_force",
        children=[child],
    )


def _build_sub_subsystem_node(
    *,
    node_id: str,
    node_name: str,
    node_code: str,
    modules: list[ToolDemandNode],
) -> ToolDemandNode:
    return ToolDemandNode(
        node_id=node_id,
        node_type="sub_subsystem",
        node_name=node_name,
        node_code=node_code,
        business_domain_id="simulated_blue_force",
        children=modules,
    )


def _build_module_node(
    *,
    node_id: str,
    node_name: str,
    node_code: str,
    component: ToolDemandNode,
) -> ToolDemandNode:
    return ToolDemandNode(
        node_id=node_id,
        node_type="module",
        node_name=node_name,
        node_code=node_code,
        business_domain_id="simulated_blue_force",
        children=[component],
    )


def _build_component_node(
    *,
    node_id: str,
    node_name: str,
    node_code: str,
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
        business_domain_id="simulated_blue_force",
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
