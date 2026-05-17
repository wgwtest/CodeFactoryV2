from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from app.config import REPO_ROOT
from app.design_converters.models import DesignConverterManifest, DesignConverterRunRequest, DesignConverterRunResult


def _env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


class RequirementToSddDifyWorkflowAdapter:
    def __init__(self, *, manifest: DesignConverterManifest, package: Any | None = None) -> None:
        self.manifest = manifest
        self.workflow = self._load_workflow()

    def run(self, request: DesignConverterRunRequest) -> DesignConverterRunResult:
        self._require_remote_configuration()
        remote_trace = self._call_remote_dify(request)
        return self._normalize_remote_result(trace=remote_trace)

    @staticmethod
    def _require_remote_configuration() -> None:
        if not _env("CODEFACTORY_P3_DIFY_API_KEY", "DIFY_API_KEY"):
            raise ValueError("DIFY_API_KEY is not configured for requirement-to-sdd-dify-workflow")

    def _call_remote_dify(self, request: DesignConverterRunRequest) -> dict:
        base_url = self._normalize_base_url(_env("CODEFACTORY_P3_DIFY_BASE_URL", "DIFY_BASE_URL") or "http://localhost")
        api_key = _env("CODEFACTORY_P3_DIFY_API_KEY", "DIFY_API_KEY")
        workflow_id = _env("CODEFACTORY_P3_DIFY_WORKFLOW_ID", "DIFY_PUBLISHED_WORKFLOW_ID", "DIFY_WORKFLOW_ID")
        response_mode = _env("CODEFACTORY_P3_DIFY_RESPONSE_MODE", "DIFY_RESPONSE_MODE") or "blocking"
        timeout_seconds = float(_env("CODEFACTORY_P3_DIFY_TIMEOUT_SECONDS", "DIFY_TIMEOUT_SECONDS") or "120")

        payload = {
            "inputs": self._remote_inputs(request),
            "response_mode": response_mode,
            "user": "codefactory-p3-session",
        }
        url = self._workflow_run_url(base_url=base_url, workflow_id=workflow_id)
        try:
            response = httpx.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout_seconds,
                trust_env=False,
            )
            response.raise_for_status()
            remote_payload = response.json()
        except httpx.HTTPError as exc:
            raise ValueError(f"remote dify workflow request failed: {exc}") from exc
        except ValueError as exc:
            raise ValueError("remote dify workflow returned non-JSON response") from exc

        data = dict(remote_payload.get("data") or {})
        workflow_status = str(data.get("status") or "").strip()
        workflow_error = str(data.get("error") or "").strip()
        workflow_run_id = str(remote_payload.get("workflow_run_id") or data.get("id") or "").strip()
        if workflow_status == "failed" or workflow_error:
            detail = workflow_error or "workflow status failed"
            raise ValueError(f"remote dify workflow failed ({workflow_run_id}): {detail}")

        outputs = dict(data.get("outputs") or {})
        result_json = outputs.get("result_json")
        if not isinstance(result_json, str) or not result_json.strip():
            raise ValueError("remote dify workflow did not return data.outputs.result_json")

        return {
            "request": {
                "url": url,
                "response_mode": response_mode,
                "user": "codefactory-p3-session",
                "inputs": payload["inputs"],
            },
            "payload": remote_payload,
            "result_json": result_json,
            "workflow_trace": {
                "remote": True,
                "local": False,
                "workflow_id": str(workflow_id or self.workflow.get("workflow_id") or ""),
                "workflow_run_id": workflow_run_id,
                "status": workflow_status,
                "response_mode": response_mode,
            },
        }

    @staticmethod
    def _workflow_run_url(*, base_url: str, workflow_id: str) -> str:
        if workflow_id:
            return f"{base_url}/workflows/{workflow_id}/run"
        return f"{base_url}/workflows/run"

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/v1"):
            return normalized
        return f"{normalized}/v1"

    def _remote_inputs(self, request: DesignConverterRunRequest) -> dict:
        input_package = dict(request.input_package or {})
        standard_document = dict(input_package.get("standard_document") or {})
        frozen_trace = {
            "input_package_id": input_package.get("input_package_id"),
            "source_document_id": input_package.get("source_document_id"),
            "frozen_at": input_package.get("frozen_at"),
            "p3_consumable": input_package.get("p3_consumable"),
        }
        return {
            "requirement_document_text": self._document_text(standard_document),
            "requirement_document_title": str(
                input_package.get("source_title")
                or standard_document.get("title")
                or "未命名需求规格说明"
            ),
            "standard_document_json": json.dumps(standard_document, ensure_ascii=False),
            "structured_spec_json": json.dumps(dict(input_package.get("structured_spec") or {}), ensure_ascii=False),
            "annotations_json": json.dumps(list(input_package.get("annotations") or []), ensure_ascii=False),
            "knowledge_binding_json": json.dumps(dict(input_package.get("knowledge_binding") or {}), ensure_ascii=False),
            "frozen_trace_json": json.dumps(frozen_trace, ensure_ascii=False),
            "target_design_profile_json": json.dumps(dict(request.target_design_profile or {}), ensure_ascii=False),
            "conversion_options_json": json.dumps(dict(request.conversion_options or {}), ensure_ascii=False),
            "quality_rules_json": json.dumps(dict(request.quality_rules or {}), ensure_ascii=False),
            "expected_output": str(dict(request.conversion_options or {}).get("expected_output") or "design_package_with_document"),
        }

    @staticmethod
    def _document_text(standard_document: dict) -> str:
        if isinstance(standard_document.get("content"), str):
            return standard_document["content"]
        if isinstance(standard_document.get("markdown"), str):
            return standard_document["markdown"]
        sections = standard_document.get("sections")
        if isinstance(sections, list):
            parts = []
            for section in sections:
                if not isinstance(section, dict):
                    continue
                title = str(section.get("title") or "").strip()
                content = str(section.get("content") or "").strip()
                if title or content:
                    parts.append(f"{title}\n{content}".strip())
            return "\n\n".join(parts)
        return json.dumps(standard_document, ensure_ascii=False)

    def _normalize_remote_result(self, *, trace: dict) -> DesignConverterRunResult:
        try:
            parsed = json.loads(str(trace["result_json"]))
        except json.JSONDecodeError as exc:
            raise ValueError("remote dify result_json is not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("remote dify result_json is not a JSON object")

        parsed = dict(parsed)
        raw_output = dict(parsed.get("raw_output") or {})
        raw_workflow_trace = {
            **dict(raw_output.get("raw_workflow_trace") or {}),
            **dict(trace.get("workflow_trace") or {}),
        }
        raw_output["raw_workflow_trace"] = raw_workflow_trace
        raw_output["raw_plugin_response"] = {"remote_payload": dict(trace.get("payload") or {})}
        parsed["raw_output"] = raw_output

        converter = {
            "converter_id": self.manifest.converter_id,
            "converter_type": self.manifest.converter_type,
            "observability_level": self.manifest.observability_level,
            **dict(parsed.get("converter") or {}),
        }
        converter["converter_id"] = self.manifest.converter_id
        converter["converter_type"] = self.manifest.converter_type
        converter["observability_level"] = self.manifest.observability_level
        parsed["converter"] = converter
        parsed.setdefault("protocol_version", self.manifest.protocol)
        parsed.setdefault("workorder_projection_candidate", {})
        parsed.setdefault("process_output", {})
        parsed.setdefault("confidence", "medium")
        parsed.setdefault("annotations", [])
        parsed.setdefault("risks", [])

        result = DesignConverterRunResult(**parsed)
        self._validate_required_output(result)
        return result

    @staticmethod
    def _validate_required_output(result: DesignConverterRunResult) -> None:
        if not result.design_document.get("sections"):
            raise ValueError("remote dify result_json missing design_document.sections")
        if not result.design_package:
            raise ValueError("remote dify result_json missing design_package")
        if not isinstance(result.traceability, list):
            raise ValueError("remote dify result_json traceability must be a list")
        if not isinstance(result.gap_list, list):
            raise ValueError("remote dify result_json gap_list must be a list")
        if not isinstance(result.review_findings, list):
            raise ValueError("remote dify result_json review_findings must be a list")

    def _load_workflow(self) -> dict:
        workflow_path = REPO_ROOT / self.manifest.package_path / "workflow.json"
        if not workflow_path.exists():
            return {}
        try:
            return json.loads(workflow_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
