from app.requirement_authoring.annotation_service import RequirementAnnotationService
from app.requirement_authoring.document_renderer import RequirementDocumentRenderer
from app.requirement_authoring.document_repository import RequirementAuthoringRepository
from app.requirement_authoring.freeze_service import RequirementFreezeService
from app.requirement_authoring.gap_checker import RequirementGapChecker
from app.requirement_authoring.models import default_template_payload


def test_requirement_authoring_modules_preserve_document_contract() -> None:
    template_payload = default_template_payload("81433")
    fields = {
        "application_name": "空域运算软件",
        "domain_scope": "空域计算分析",
        "application_scope": "空域计算分析任务链",
        "business_goals": "支撑空域计算分析的任务闭环。",
        "main_scenarios": "导入数据、执行计算、查看结果。",
        "usage_modes": "专家单人分析并提交结果。",
        "in_scope": "数据导入、计算分析、结果输出。",
        "out_of_scope": "不包含自动优化推荐。",
        "target_users": "领域专家",
        "main_process": "导入数据后计算分析",
        "normal_flow": "导入数据、执行计算、生成结果。",
        "situational_display": "展示计算任务状态、输入数据和结果摘要。",
        "gis_analysis_tools": "支持基础空间查询和结果定位。",
        "deployment_analysis": "支持部署点位影响范围辅助分析。",
        "result_outputs": "输出计算结果表和分析图件。",
        "collaboration_mode": "支持结果提交和专家复核。",
        "exception_flow": "缺数据时阻断并提示。",
        "input_data_sources": "任务数据、基础地理数据和配置参数。",
        "input_data_mode": "人工导入和本地文件读取。",
        "performance_requirements": "常规查询 2 秒内返回。",
        "reliability_requirements": "关键计算失败时保留错误记录。",
        "security_requirements": "按用户身份控制访问。",
        "permission_model": "领域专家可编辑，审核人员可复核。",
        "deployment_environment": "内网环境部署。",
        "accuracy_constraints": "辅助研判级精度。",
        "acceptance_scenarios": "完成一次从数据导入到结果输出的任务链。",
        "acceptance_criteria": "核心流程可闭环验收。",
    }

    document = RequirementDocumentRenderer().render_document(template_payload, fields)
    assert document["title"] == "空域运算软件需求规格说明"
    assert document["sections"][2]["clauses"][1]["content"] == "核心流程为导入数据后计算分析；正常流程包括：导入数据、执行计算、生成结果。"

    annotations = RequirementAnnotationService().build_annotations(template_payload, fields)
    assert annotations[0]["clause_id"] == "REQ-1.1"
    assert annotations[0]["pending_confirmations"] == []

    check_result = RequirementGapChecker().run(template_payload, fields)
    assert check_result["blocking_count"] == 0
    assert check_result["passed_count"] == 21

    frozen_package = RequirementFreezeService().build_frozen_package(
        standard_document=document,
        annotations=annotations,
        fields=fields,
        archive_ids=["20161116-nas"],
        frozen_at="2026-05-02T00:00:00+00:00",
    )
    assert frozen_package["p3_consumable"] is True
    assert frozen_package["structured_spec"]["application"]["name"] == "空域运算软件"
    assert frozen_package["structured_spec"]["application"]["goals"] == "支撑空域计算分析的任务闭环。"
    assert frozen_package["structured_spec"]["capabilities"]["gis_analysis_tools"] == "支持基础空间查询和结果定位。"
    assert frozen_package["structured_spec"]["processes"][0]["source_archive_id"] == "20161116-nas"


def test_requirement_authoring_repository_only_exposes_document_persistence() -> None:
    repository_methods = set(dir(RequirementAuthoringRepository))
    assert "list_documents" in repository_methods
    assert "get_document" in repository_methods
    assert "add_document" in repository_methods
    assert "save_document" in repository_methods
    assert "delete_document" in repository_methods
    assert "list_templates" not in repository_methods
    assert "get_template" not in repository_methods
    assert "add_template" not in repository_methods
    assert "save_template" not in repository_methods
    assert "ensure_default_templates" not in repository_methods
