from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ConverterType = Literal["local_package", "dify_workflow", "remote_service"]
ObservabilityLevel = Literal["full", "limited", "none"]

DESIGN_CONVERTER_CAPABILITY_KEYS = (
    "design_document",
    "design_package",
    "traceability",
    "gap_list",
    "review_findings",
    "p4_workorder_projection",
)


class DesignConverterManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    converter_id: str
    name: str
    converter_type: ConverterType
    document_type: str = "software_design_description"
    protocol: str = "p3-design-converter-protocol@1"
    status: str = "active"
    priority: int = 100
    capabilities: dict[str, bool] = Field(default_factory=dict)
    requires: dict[str, Any] = Field(default_factory=dict)
    adapter_module: str
    adapter_class: str
    package_path: str = ""
    aliases: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_adapter_entry(self) -> "DesignConverterManifest":
        missing = []
        if not self.adapter_module.strip():
            missing.append("adapter_module")
        if not self.adapter_class.strip():
            missing.append("adapter_class")
        if missing:
            raise ValueError(f"design converter manifest missing adapter entry: {', '.join(missing)}")
        return self

    @property
    def observability_level(self) -> ObservabilityLevel:
        if all(bool(self.capabilities.get(key)) for key in DESIGN_CONVERTER_CAPABILITY_KEYS):
            return "limited"
        if any(bool(self.capabilities.get(key)) for key in DESIGN_CONVERTER_CAPABILITY_KEYS):
            return "limited"
        return "none"

    def to_api(self) -> dict[str, Any]:
        return {
            "converter_id": self.converter_id,
            "name": self.name,
            "converter_type": self.converter_type,
            "document_type": self.document_type,
            "protocol": self.protocol,
            "status": self.status,
            "priority": self.priority,
            "capabilities": dict(self.capabilities),
            "requires": dict(self.requires),
            "adapter_module": self.adapter_module,
            "adapter_class": self.adapter_class,
            "package_path": self.package_path,
            "aliases": list(self.aliases),
            "observability_level": self.observability_level,
        }


class DesignConverterRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_version: str
    session: dict[str, Any]
    input_package: dict[str, Any]
    target_design_profile: dict[str, Any]
    conversion_options: dict[str, Any]
    quality_rules: dict[str, Any]


class DesignConverterRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_version: str
    converter: dict[str, Any]
    design_document: dict[str, Any]
    design_package: dict[str, Any]
    traceability: list[dict[str, Any]]
    gap_list: list[dict[str, Any]]
    review_findings: list[dict[str, Any]]
    workorder_projection_candidate: dict[str, Any]
    process_output: dict[str, Any]
    raw_output: dict[str, Any]
    confidence: str = "medium"
    annotations: list[Any] = Field(default_factory=list)
    risks: list[Any] = Field(default_factory=list)
