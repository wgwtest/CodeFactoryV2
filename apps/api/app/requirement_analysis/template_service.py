from __future__ import annotations

import json
import re
from pathlib import Path

from app.requirement_analysis.template_parser import MarkdownTemplateParser


class RequirementAnalysisTemplateService:
    """File-backed Markdown template instances used by the Requirement Analysis Lab."""

    TEMPLATE_ROOT = (
        Path(__file__).resolve().parents[4]
        / "DOC"
        / "JB_DOC"
        / "02-软件工厂产物模板中心"
        / "01-需求与设计主链模板"
        / "01-需求规格模板"
    )
    BASE_TEMPLATE_DIR_NAME = "基础模板"
    CUSTOM_TEMPLATE_DIR_NAME = "自定义模板"
    MANIFEST_FILE = "manifest.json"

    BASE_TEMPLATE_FILES = {
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
    def list_base_templates(self) -> dict:
        items = [
            self._base_template_summary(template_id, metadata)
            for template_id, metadata in self.BASE_TEMPLATE_FILES.items()
            if self._base_template_path(metadata).exists()
        ]
        items.extend(self._read_promoted_base_templates())
        return {"items": items}

    def list_templates(self) -> dict:
        return {"items": [self._instance_summary(instance) for instance in self._read_manifest()]}

    def get_template(self, template_id: str) -> dict | None:
        instance = self._find_instance(template_id)
        if instance is None:
            return None
        path = self._instance_path(instance["template_id"])
        if not path.exists():
            return None
        return {
            **self._instance_summary(instance),
            "format": "markdown",
            "content": path.read_text(encoding="utf-8"),
        }

    def resolve_runtime_payload(self, template_id: str) -> dict | None:
        detail = self.get_template(template_id)
        if detail is None:
            return None
        content = str(detail.get("content") or "")
        parsed = MarkdownTemplateParser().parse(content)
        return {
            **detail,
            "sections": list(parsed["sections"]),
            "parse_diagnostics": list(parsed["parse_diagnostics"]),
        }

    def create_template(self, *, base_template_id: str, name: str, description: str = "") -> dict | None:
        canonical_base_id = self._canonical_base_template_id(base_template_id)
        base_metadata = self._base_metadata(canonical_base_id)
        if base_metadata is None:
            return None
        manifest = self._read_manifest()
        template_id = self._new_instance_id(canonical_base_id, name, manifest)
        instance = {
            "template_id": template_id,
            "template_code": str(base_metadata["template_code"]),
            "base_template_id": canonical_base_id,
            "base_template_name": str(base_metadata["name"]),
            "name": name.strip() or f"{base_metadata['name']}实例",
            "description": description.strip() or f"基于 {base_metadata['template_code']} 扩充的 Lab 模板实例。",
            "status": "available",
        }
        manifest.append(instance)
        self._write_manifest(manifest)
        self._write_instance_content(template_id, self._base_template_path(base_metadata).read_text(encoding="utf-8"))
        return self.get_template(template_id)

    def save_template(self, template_id: str, content: str, *, name: str | None = None, description: str | None = None) -> dict | None:
        manifest = self._read_manifest()
        instance = next((item for item in manifest if item["template_id"] == template_id), None)
        if instance is None:
            return None
        if name is not None:
            instance["name"] = name.strip() or instance["name"]
        if description is not None:
            instance["description"] = description.strip()
        self._write_manifest(manifest)
        self._write_instance_content(template_id, content)
        return self.get_template(template_id)

    def delete_template(self, template_id: str) -> dict | None:
        manifest = self._read_manifest()
        if not any(item["template_id"] == template_id for item in manifest):
            return None
        manifest = [item for item in manifest if item["template_id"] != template_id]
        self._write_manifest(manifest)
        path = self._instance_path(template_id)
        if path.exists():
            path.unlink()
        return {"deleted": True, "template_id": template_id}

    def save_template_as_base(self, template_id: str) -> dict | None:
        detail = self.get_template(template_id)
        if detail is None:
            return None
        manifest = self._read_base_manifest()
        new_template_id = self._new_promoted_base_id(detail["name"], manifest)
        file_name = self._new_promoted_base_file_name(detail["name"], manifest)
        base_item = {
            "template_id": new_template_id,
            "template_code": self._new_promoted_base_code(manifest),
            "name": str(detail["name"]),
            "description": "基础模板依据，只读，不作为 Lab 会话直接编辑对象。",
            "status": "available",
            "file_name": file_name,
            "source_template_id": str(detail["template_id"]),
        }
        self._base_template_root().mkdir(parents=True, exist_ok=True)
        (self._base_template_root() / file_name).write_text(str(detail["content"]), encoding="utf-8")
        manifest.append(base_item)
        self._write_base_manifest(manifest)
        return self._base_template_summary(base_item["template_id"], base_item)

    def _write_instance_content(self, template_id: str, content: str) -> None:
        path = self._instance_path(template_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = content if content.endswith("\n") else f"{content}\n"
        path.write_text(normalized, encoding="utf-8")

    def _read_manifest(self) -> list[dict]:
        self._custom_template_root().mkdir(parents=True, exist_ok=True)
        manifest_path = self._manifest_path()
        if not manifest_path.exists():
            self._write_manifest([])
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            payload = {"items": []}
        items = payload.get("items") if isinstance(payload, dict) else []
        return [self._normalize_instance(item) for item in items if isinstance(item, dict)]

    def _write_manifest(self, items: list[dict]) -> None:
        self._custom_template_root().mkdir(parents=True, exist_ok=True)
        self._manifest_path().write_text(
            json.dumps({"items": items}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def _canonical_base_template_id(cls, template_id: str) -> str:
        digits = "".join(char for char in template_id if char.isdigit())
        if digits.startswith("82259"):
            return "82259号"
        if digits.startswith("81433"):
            return "81433号"
        if digits.startswith("custom"):
            return template_id
        return template_id

    def _base_metadata(self, template_id: str) -> dict | None:
        return self.BASE_TEMPLATE_FILES.get(self._canonical_base_template_id(template_id))

    def _find_instance(self, template_id: str) -> dict | None:
        manifest = self._read_manifest()
        exact = next((item for item in manifest if item["template_id"] == template_id), None)
        return exact

    def _base_template_path(self, metadata: dict) -> Path:
        primary = self._base_template_root() / str(metadata["file_name"])
        if primary.exists():
            return primary
        return self._base_template_root() / f"{metadata['template_code']}.md"

    def _instance_path(self, template_id: str) -> Path:
        return self._custom_template_root() / f"{template_id}.md"

    def _manifest_path(self) -> Path:
        return self._custom_template_root() / self.MANIFEST_FILE

    def _base_manifest_path(self) -> Path:
        return self._base_template_root() / self.MANIFEST_FILE

    def _base_template_root(self) -> Path:
        return self.TEMPLATE_ROOT / self.BASE_TEMPLATE_DIR_NAME

    def _custom_template_root(self) -> Path:
        return self.TEMPLATE_ROOT / self.CUSTOM_TEMPLATE_DIR_NAME

    def _new_instance_id(self, base_template_id: str, name: str, manifest: list[dict]) -> str:
        base_code = str(self.BASE_TEMPLATE_FILES[base_template_id]["template_code"])
        slug = self._slugify(name) or "instance"
        used = {str(item["template_id"]) for item in manifest}
        candidate = f"xg-template-{base_code}-{slug}"
        suffix = 2
        while candidate in used:
            candidate = f"xg-template-{base_code}-{slug}-{suffix}"
            suffix += 1
        return candidate

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", value.strip().lower()).strip("-")
        if normalized:
            return normalized[:80]
        return "instance"

    def _read_base_manifest(self) -> list[dict]:
        path = self._base_manifest_path()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            payload = {"items": []}
        items = payload.get("items") if isinstance(payload, dict) else []
        return [self._normalize_base_template(item) for item in items if isinstance(item, dict)]

    def _write_base_manifest(self, items: list[dict]) -> None:
        self._base_template_root().mkdir(parents=True, exist_ok=True)
        self._base_manifest_path().write_text(
            json.dumps({"items": items}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _read_promoted_base_templates(self) -> list[dict]:
        return [self._base_template_summary(item["template_id"], item) for item in self._read_base_manifest()]

    def _new_promoted_base_id(self, name: str, manifest: list[dict]) -> str:
        slug = self._slugify(name)
        used = {str(item["template_id"]) for item in manifest}.union(self.BASE_TEMPLATE_FILES.keys())
        candidate = f"custom-{slug}"
        suffix = 2
        while candidate in used:
            candidate = f"custom-{slug}-{suffix}"
            suffix += 1
        return candidate

    def _new_promoted_base_code(self, manifest: list[dict]) -> str:
        used_numbers = []
        for item in manifest:
            code = str(item.get("template_code") or "")
            digits = "".join(char for char in code if char.isdigit())
            if digits:
                used_numbers.append(int(digits))
        next_number = (max(used_numbers) + 1) if used_numbers else 90001
        return f"CUSTOM-{next_number}"

    def _new_promoted_base_file_name(self, name: str, manifest: list[dict]) -> str:
        slug = self._slugify(name).replace("-", "")
        candidate = f"03-{slug or 'custom-base-template'}.md"
        used = {str(item.get('file_name') or '') for item in manifest}
        suffix = 2
        while candidate in used or (self._base_template_root() / candidate).exists():
            candidate = f"03-{slug or 'custom-base-template'}-{suffix}.md"
            suffix += 1
        return candidate

    @staticmethod
    def _normalize_base_template(item: dict) -> dict:
        return {
            "template_id": str(item.get("template_id") or "custom-base"),
            "template_code": str(item.get("template_code") or "CUSTOM-90001"),
            "name": str(item.get("name") or "自定义基础模板"),
            "description": "基础模板依据，只读，不作为 Lab 会话直接编辑对象。",
            "status": str(item.get("status") or "available"),
            "file_name": str(item.get("file_name") or "03-custom-base-template.md"),
            "source_template_id": str(item.get("source_template_id") or ""),
        }

    @staticmethod
    def _base_template_summary(template_id: str, metadata: dict) -> dict:
        return {
            "template_id": template_id,
            "template_code": str(metadata["template_code"]),
            "name": str(metadata["name"]),
            "description": "基础模板依据，只读，不作为 Lab 会话直接编辑对象。",
            "status": str(metadata["status"]),
        }

    def _normalize_instance(self, item: dict) -> dict:
        base_template_id = self._canonical_base_template_id(str(item.get("base_template_id") or item.get("template_id") or "81433号"))
        base_metadata = self._base_metadata(base_template_id) or {
            "template_code": str(item.get("template_code") or "81433"),
            "name": str(item.get("base_template_name") or "自定义基础模板"),
        }
        return {
            "template_id": str(item.get("template_id") or "xg-template-instance"),
            "template_code": str(item.get("template_code") or base_metadata["template_code"]),
            "base_template_id": base_template_id,
            "base_template_name": str(item.get("base_template_name") or base_metadata["name"]),
            "name": str(item.get("name") or base_metadata["name"]),
            "description": str(item.get("description") or f"基于 {base_metadata['template_code']} 扩充的 Lab 模板实例。"),
            "status": str(item.get("status") or "available"),
        }

    @staticmethod
    def _instance_summary(instance: dict) -> dict:
        return {
            "template_id": str(instance["template_id"]),
            "template_code": str(instance["template_code"]),
            "base_template_id": str(instance["base_template_id"]),
            "base_template_name": str(instance["base_template_name"]),
            "name": str(instance["name"]),
            "description": str(instance["description"]),
            "status": str(instance["status"]),
        }
