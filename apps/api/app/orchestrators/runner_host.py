from __future__ import annotations

import importlib.util
import json
import sys
from typing import Any

from app.orchestrators.contract_validator import OrchestratorContractValidator
from app.orchestrators.package_loader import OrchestratorPackageLoader
from app.orchestrators.stage_adoption_policy_resolver import StageAdoptionPolicyResolver
from app.orchestrators.stage_prompt_bundle_builder import StagePromptBundleBuilder
from app.orchestrators.stage_prompt_resolver import StagePromptResolver
from app.orchestrators.stage_schema_resolver import StageSchemaResolver


class OrchestratorRunnerHost:
    def __init__(
        self,
        *,
        loader: OrchestratorPackageLoader | None = None,
        validator: OrchestratorContractValidator | None = None,
        stage_prompt_resolver: StagePromptResolver | None = None,
        stage_schema_resolver: StageSchemaResolver | None = None,
        stage_adoption_policy_resolver: StageAdoptionPolicyResolver | None = None,
        stage_prompt_bundle_builder: StagePromptBundleBuilder | None = None,
    ) -> None:
        self.loader = loader or OrchestratorPackageLoader()
        self.validator = validator or OrchestratorContractValidator()
        self.stage_prompt_resolver = stage_prompt_resolver or StagePromptResolver()
        self.stage_schema_resolver = stage_schema_resolver or StageSchemaResolver()
        self.stage_adoption_policy_resolver = stage_adoption_policy_resolver or StageAdoptionPolicyResolver()
        self.stage_prompt_bundle_builder = stage_prompt_bundle_builder or StagePromptBundleBuilder()

    def build_stage_prompt_bundle(
        self,
        orchestrator_id: str,
        *,
        stage: dict,
        context: dict[str, Any],
        output_schema: dict[str, Any] | None = None,
        extra_prompt_bundle: dict[str, Any] | None = None,
    ) -> dict:
        loaded = self.loader.load(orchestrator_id)
        prompt = self.stage_prompt_resolver.resolve(loaded, stage=stage)
        schema = self.stage_schema_resolver.resolve(loaded, stage=stage, fallback_schema=output_schema or {})
        adoption_policy = self.stage_adoption_policy_resolver.resolve(loaded, stage=stage)
        return self.stage_prompt_bundle_builder.build(
            loaded=loaded,
            stage=stage,
            prompt=prompt,
            context=context,
            output_schema=schema,
            adoption_policy=adoption_policy,
            extra_prompt_bundle=extra_prompt_bundle,
        )

    def build_provider_prompt_bundle(
        self,
        orchestrator_id: str,
        *,
        context: dict[str, Any],
        output_schema: dict[str, Any],
        extra_prompt_bundle: dict[str, Any] | None = None,
    ) -> dict:
        return self.build_stage_prompt_bundle(
            orchestrator_id,
            stage={"stage_id": "write", "stage_kind": "write", "prompt_id": "write"},
            context=context,
            output_schema=output_schema,
            extra_prompt_bundle=extra_prompt_bundle,
        )

    def normalize_output(
        self,
        payload: dict[str, Any],
        *,
        provider_id: str,
        model: str,
        write_policy: str,
        raw_response: dict[str, Any] | None = None,
    ) -> dict:
        return self.validator.normalize_turn_output(
            payload,
            provider_id=provider_id,
            model=model,
            write_policy=write_policy,
            raw_response=raw_response,
        )

    def execute_local_runner(self, orchestrator_id: str, *, context: dict[str, Any]) -> dict:
        loaded = self.loader.load(orchestrator_id)
        if loaded.package.mode != "local_runner":
            raise ValueError("orchestrator is not a local runner")
        if not loaded.entry_path:
            raise RuntimeError("local runner orchestrator missing entry path")

        module = self._load_runner_module(orchestrator_id, loaded.entry_path)
        run_turn = getattr(module, "run_turn", None)
        if not callable(run_turn):
            raise RuntimeError(f"local runner {loaded.entry_path} must expose run_turn(context)")

        output = run_turn(context)
        if not isinstance(output, dict):
            raise RuntimeError(f"local runner {loaded.entry_path} must return a dict")

        raw_response = dict(output.get("raw_model_response") or {})
        output["raw_model_response"] = {
            **raw_response,
            "orchestrator_id": loaded.package.orchestrator_id,
            "mode": loaded.package.mode,
            "mock": raw_response.get("mock", True),
            "runner_invoked": True,
            "runner_entry": loaded.entry_path,
        }
        return output

    @staticmethod
    def _load_runner_module(orchestrator_id: str, entry_path: str):
        module_name = f"_codefactory_orchestrator_{orchestrator_id.replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, entry_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load local runner: {entry_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
