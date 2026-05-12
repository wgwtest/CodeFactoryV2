from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.archive_knowledge.contracts.common import ArtifactRef


QualityFindingScope = Literal["item", "relation", "publication", "evidence", "category", "system_output"]
QualitySeverity = Literal["info", "warning", "blocked"]
QualitySuggestedAction = Literal[
    "accept",
    "manual_review",
    "fix_contract",
    "add_evidence",
    "add_definition",
    "split",
    "merge",
    "reject",
    "defer_publish",
]


class QualityFinding(BaseModel):
    finding_id: str
    scope: QualityFindingScope
    severity: QualitySeverity
    code: str
    message: str
    target_id: str | None = None
    target_type: str | None = None
    evidence_refs: list[ArtifactRef] = Field(default_factory=list)
    suggested_action: QualitySuggestedAction = "manual_review"
    blocking_publish: bool = False
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class QualityReportSummary(BaseModel):
    finding_count: int = 0
    blocked_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    publish_blocked: bool = False


class QualityFindingReport(BaseModel):
    report_id: str
    archive_id: str
    generated_at: str
    resolution_snapshot_id: str | None = None
    publication_snapshot_id: str | None = None
    findings: list[QualityFinding] = Field(default_factory=list)
    summary: QualityReportSummary = Field(default_factory=QualityReportSummary)


def summarize_findings(findings: list[QualityFinding]) -> QualityReportSummary:
    blocked_count = sum(1 for finding in findings if finding.severity == "blocked")
    warning_count = sum(1 for finding in findings if finding.severity == "warning")
    info_count = sum(1 for finding in findings if finding.severity == "info")
    return QualityReportSummary(
        finding_count=len(findings),
        blocked_count=blocked_count,
        warning_count=warning_count,
        info_count=info_count,
        publish_blocked=any(finding.blocking_publish for finding in findings),
    )
