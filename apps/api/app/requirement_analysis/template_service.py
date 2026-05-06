from __future__ import annotations

import json
import re
from pathlib import Path


class RequirementAnalysisTemplateService:
    """File-backed Markdown template instances used by the Requirement Analysis Lab."""

    TEMPLATE_ROOT = (
        Path(__file__).resolve().parents[4]
        / "DOC"
        / "JB_DOC"
        / "02-软件工厂产物模板中心"
        / "01-需求与设计主链模板"
    )
    INSTANCE_ROOT = (
        Path(__file__).resolve().parents[4]
        / "DOC"
        / "JB_DOC"
        / "03-项目实例与样例"
        / "P2-需求分析Lab模板实例"
    )
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
    DEFAULT_INSTANCE_IDS = {
        "81433号": "xg-template-81433-default",
        "82259号": "xg-template-82259-default",
    }

    def list_base_templates(self) -> dict:
        return {
            "items": [
                self._base_template_summary(template_id, metadata)
                for template_id, metadata in self.BASE_TEMPLATE_FILES.items()
                if self._base_template_path(metadata).exists()
            ]
        }

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

    def _write_instance_content(self, template_id: str, content: str) -> None:
        path = self._instance_path(template_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = content if content.endswith("\n") else f"{content}\n"
        path.write_text(normalized, encoding="utf-8")

    def _read_manifest(self) -> list[dict]:
        self._ensure_default_instances()
        manifest_path = self._manifest_path()
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            payload = {"items": []}
        items = payload.get("items") if isinstance(payload, dict) else []
        return [self._normalize_instance(item) for item in items if isinstance(item, dict)]

    def _write_manifest(self, items: list[dict]) -> None:
        self.INSTANCE_ROOT.mkdir(parents=True, exist_ok=True)
        self._manifest_path().write_text(
            json.dumps({"items": items}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _ensure_default_instances(self) -> None:
        self.INSTANCE_ROOT.mkdir(parents=True, exist_ok=True)
        manifest_path = self._manifest_path()
        if manifest_path.exists():
            return
        items = []
        for base_template_id, metadata in self.BASE_TEMPLATE_FILES.items():
            base_path = self._base_template_path(metadata)
            if not base_path.exists():
                continue
            instance_id = self.DEFAULT_INSTANCE_IDS[base_template_id]
            items.append(
                {
                    "template_id": instance_id,
                    "template_code": str(metadata["template_code"]),
                    "base_template_id": base_template_id,
                    "base_template_name": str(metadata["name"]),
                    "name": str(metadata["name"]),
                    "description": f"基于 {metadata['template_code']} 的默认实例模板。",
                    "status": str(metadata["status"]),
                }
            )
            instance_path = self._instance_path(instance_id)
            if not instance_path.exists():
                self._write_instance_content(instance_id, base_path.read_text(encoding="utf-8"))
        self._write_manifest(items)

    @classmethod
    def _canonical_base_template_id(cls, template_id: str) -> str:
        digits = "".join(char for char in template_id if char.isdigit())
        if digits.startswith("82259"):
            return "82259号"
        if digits.startswith("81433"):
            return "81433号"
        return template_id

    def _base_metadata(self, template_id: str) -> dict | None:
        return self.BASE_TEMPLATE_FILES.get(self._canonical_base_template_id(template_id))

    def _find_instance(self, template_id: str) -> dict | None:
        manifest = self._read_manifest()
        exact = next((item for item in manifest if item["template_id"] == template_id), None)
        if exact is not None:
            return exact
        canonical_base_id = self._canonical_base_template_id(template_id)
        default_instance_id = self.DEFAULT_INSTANCE_IDS.get(canonical_base_id)
        if default_instance_id is None:
            return None
        return next((item for item in manifest if item["template_id"] == default_instance_id), None)

    def _base_template_path(self, metadata: dict) -> Path:
        primary = self.TEMPLATE_ROOT / str(metadata["file_name"])
        if primary.exists():
            return primary
        return self.TEMPLATE_ROOT / f"{metadata['template_code']}.md"

    def _instance_path(self, template_id: str) -> Path:
        return self.INSTANCE_ROOT / f"{template_id}.md"

    def _manifest_path(self) -> Path:
        return self.INSTANCE_ROOT / self.MANIFEST_FILE

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
        base_metadata = self._base_metadata(base_template_id) or self.BASE_TEMPLATE_FILES["81433号"]
        return {
            "template_id": str(item.get("template_id") or self.DEFAULT_INSTANCE_IDS.get(base_template_id) or "xg-template-81433-default"),
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
