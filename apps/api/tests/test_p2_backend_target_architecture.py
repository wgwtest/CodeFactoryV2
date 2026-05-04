from importlib import import_module


def test_p2_backend_target_modules_are_exposed() -> None:
    requirement_configuration = import_module("app.requirement_configuration")
    requirement_exchange = import_module("app.requirement_exchange")
    requirement_authoring = import_module("app.requirement_authoring")

    assert requirement_configuration is not None
    assert requirement_exchange is not None
    assert requirement_authoring is not None


def test_p2_backend_target_services_can_be_imported() -> None:
    template_application_service = import_module("app.requirement_configuration.template_application_service")
    exchange_application_service = import_module("app.requirement_exchange.exchange_application_service")
    document_application_service = import_module("app.requirement_authoring.document_application_service")
    analysis_application_service = import_module("app.requirement_analysis.session_application_service")

    assert hasattr(template_application_service, "RequirementConfigurationApplicationService")
    assert hasattr(exchange_application_service, "RequirementExchangeApplicationService")
    assert hasattr(document_application_service, "RequirementAuthoringApplicationService")
    assert hasattr(analysis_application_service, "RequirementAnalysisApplicationService")
