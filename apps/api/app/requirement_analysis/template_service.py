from __future__ import annotations

from pathlib import Path


class RequirementAnalysisTemplateService:
    """File-backed Markdown templates used by the Requirement Analysis Lab."""

    TEMPLATE_ROOT = (
        Path(__file__).resolve().parents[4]
        / "DOC"
        / "JB_DOC"
        / "02-软件工厂产物模板中心"
        / "01-需求与设计主链模板"
    )

    TEMPLATE_FILES = {
        "81433号": {
            "template_code": "81433",
            "name": "软件级需求规格说明模板",
            "file_name": "01-81433-软件级需求规格模板.md",
            "status": "active",
        },
        "82259号": {
            "template_code": "82259",
            "name": "平台级需求规格说明模板",
            "file_name": "02-82259-平台级规格模板.md",
            "status": "available",
        },
    }

    def list_templates(self) -> dict:
        return {
            "items": [
                self._template_summary(template_id, metadata)
                for template_id, metadata in self.TEMPLATE_FILES.items()
                if self._template_path(metadata).exists()
            ]
        }

    def get_template(self, template_id: str) -> dict | None:
        metadata = self._metadata(template_id)
        if metadata is None:
            return None
        path = self._template_path(metadata)
        if not path.exists():
            return None
        return {
            **self._template_summary(self._canonical_template_id(template_id), metadata),
            "format": "markdown",
            "content": path.read_text(encoding="utf-8"),
        }

    def save_template(self, template_id: str, content: str) -> dict | None:
        metadata = self._metadata(template_id)
        if metadata is None:
            return None
        path = self._template_path(metadata)
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = content if content.endswith("\n") else f"{content}\n"
        path.write_text(normalized, encoding="utf-8")
        return self.get_template(template_id)

    def _metadata(self, template_id: str) -> dict | None:
        return self.TEMPLATE_FILES.get(self._canonical_template_id(template_id))

    @classmethod
    def _canonical_template_id(cls, template_id: str) -> str:
        digits = "".join(char for char in template_id if char.isdigit())
        if digits.startswith("82259"):
            return "82259号"
        if digits.startswith("81433"):
            return "81433号"
        return template_id

    def _template_path(self, metadata: dict) -> Path:
        primary = self.TEMPLATE_ROOT / str(metadata["file_name"])
        if primary.exists():
            return primary
        return self.TEMPLATE_ROOT / f"{metadata['template_code']}.md"

    @staticmethod
    def _template_summary(template_id: str, metadata: dict) -> dict:
        return {
            "template_id": template_id,
            "template_code": str(metadata["template_code"]),
            "name": str(metadata["name"]),
            "description": "Lab 可编辑 Markdown 模板。",
            "status": str(metadata["status"]),
        }
