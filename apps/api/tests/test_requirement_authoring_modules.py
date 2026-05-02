from app.requirement_authoring.annotation_service import RequirementAnnotationService
from app.requirement_authoring.document_renderer import RequirementDocumentRenderer
from app.requirement_authoring.freeze_service import RequirementFreezeService
from app.requirement_authoring.gap_checker import RequirementGapChecker
from app.requirement_authoring.models import default_template_payload


def test_requirement_authoring_modules_preserve_document_contract() -> None:
    template_payload = default_template_payload("81433")
    fields = {
        "application_name": "空域运算软件",
        "domain_scope": "空域计算分析",
        "target_users": "领域专家",
        "main_process": "导入数据后计算分析",
        "normal_flow": "导入数据、执行计算、生成结果。",
        "exception_flow": "缺数据时阻断并提示。",
        "acceptance_criteria": "核心流程可闭环验收。",
        "non_functional": "关键计算结果可追溯。",
    }

    document = RequirementDocumentRenderer().render_document(template_payload, fields)
    assert document["title"] == "空域运算软件需求规格说明"
    assert document["sections"][2]["clauses"][1]["content"] == "核心流程为导入数据后计算分析；正常流程包括：导入数据、执行计算、生成结果。"

    annotations = RequirementAnnotationService().build_annotations(template_payload, fields)
    assert annotations[0]["clause_id"] == "REQ-1.1"
    assert annotations[0]["pending_confirmations"] == []

    check_result = RequirementGapChecker().run(template_payload, fields)
    assert check_result["blocking_count"] == 0
    assert check_result["passed_count"] == 8

    frozen_package = RequirementFreezeService().build_frozen_package(
        standard_document=document,
        annotations=annotations,
        fields=fields,
        archive_ids=["20161116-nas"],
        frozen_at="2026-05-02T00:00:00+00:00",
    )
    assert frozen_package["p3_consumable"] is True
    assert frozen_package["structured_spec"]["application"]["name"] == "空域运算软件"
    assert frozen_package["structured_spec"]["processes"][0]["source_archive_id"] == "20161116-nas"
