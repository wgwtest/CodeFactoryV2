from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from app.archive_knowledge.document_artifacts import DocumentArtifactRepository
from app.archive_knowledge.repository import JsonPublishedKnowledgeRepository
from app.archive_knowledge.runtime_indexes_snapshots_apis import build_indexes_snapshots_apis_snapshot
from app.archive_knowledge.runtime_repository import DocumentRuntimeRepository
from app.archive_knowledge.runtime_snapshot_service import (
    DocumentRuntimeSnapshotService,
    RUNTIME_SNAPSHOT_CONTRACT_VERSION,
)
from app.archive_knowledge.service import ArchiveKnowledgeService
from app.archive_knowledge.runtime_contract import (
    DocumentRuntimeContract,
    RuleExecutionRecord,
    RuntimeAction,
    RuntimeEvent,
    RuntimeGraphEdge,
    RuntimeGraphNode,
    RuntimeObserverMode,
    RuntimeObserverPayload,
    RuntimeOrigin,
    RuntimeStageDefinition,
    RuntimeStageGraph,
    RuntimeStageSnapshot,
    RuntimeStatus,
    RuntimeSummaryField,
    RuntimeSummarySection,
    STAGE_DEFINITIONS,
)


class ArchiveDocumentRuntimeService:
    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)
        self.artifact_repository = DocumentArtifactRepository(self.output_root)
        self.published_repository = JsonPublishedKnowledgeRepository(self.output_root)
        self.runtime_repository = DocumentRuntimeRepository(self.output_root)
        self.runtime_snapshot_service = DocumentRuntimeSnapshotService(self.output_root)
        self.knowledge_service = ArchiveKnowledgeService(self.output_root, published_repository=self.published_repository)

    def get_document_runtime(self, archive_id: str, document_id: str) -> dict | None:
        build_state = self.artifact_repository.load_build_state(archive_id) or {}
        document_source = self.artifact_repository.get_document_source_info(archive_id, document_id)
        if document_source is None:
            document_source = self._load_build_state_document_source(build_state, document_id)
        try:
            contribution = self.artifact_repository.load_document_contribution(archive_id, document_id)
        except FileNotFoundError:
            contribution = None
        used_legacy_source = False
        if document_source is None and contribution is None:
            legacy = self._load_legacy_document_runtime_source(archive_id, document_id)
            if legacy is None:
                return None
            used_legacy_source = True
            document_source = legacy["document_source"]
            contribution = legacy["contribution"]

        document = (contribution or {}).get("document") or document_source or {}
        publication = self.published_repository.get_publication_overview(
            archive_id,
            working_summary=(contribution or {}).get("summary", {}),
        )
        persisted_stage_ids = self._ordered_stage_ids(
            self.runtime_repository.list_stage_snapshot_ids(archive_id, document_id)
        )
        context = self._build_context(
            archive_id=archive_id,
            document_id=document_id,
            document=document,
            document_source=document_source or {},
            contribution=contribution or {},
            build_state=build_state,
            publication=publication,
        )
        context["policy_snapshot"] = self._normalize_policy_snapshot(
            context.get("policy_snapshot"),
            archive_id=archive_id,
            persisted_stage_ids=persisted_stage_ids,
            document_id=document_id,
        )
        if (
            contribution
            and not used_legacy_source
            and not context["is_current_build_document"]
        ):
            needs_backfill = not persisted_stage_ids
            stale_stage_ids = (
                self._persisted_snapshots_requiring_refresh(
                    archive_id,
                    document_id,
                    persisted_stage_ids,
                )
                if persisted_stage_ids
                else []
            )
            needs_refresh = bool(stale_stage_ids)
            if needs_backfill or needs_refresh:
                parsed_document = self.runtime_snapshot_service.load_or_derive_parsed_document(document_source or {})
                can_refresh_parse_stages = (
                    parsed_document is not None and getattr(parsed_document, "parser_version", None) != "derived"
                )
                if needs_backfill or can_refresh_parse_stages:
                    self.runtime_snapshot_service.persist_document_runtime_snapshots(
                        archive_id=archive_id,
                        archive_name=build_state.get("archive_name") or archive_id,
                        document_source=document_source or {},
                        contribution=contribution,
                        mode="runtime_backfill",
                        intake_timestamp=build_state.get("started_at"),
                        parsed_document=parsed_document,
                    )
                    persisted_stage_ids = self._ordered_stage_ids(
                        self.runtime_repository.list_stage_snapshot_ids(archive_id, document_id)
                    )
                elif needs_refresh:
                    refreshed_stage_ids = self.runtime_snapshot_service.refresh_runtime_stage_snapshots(
                        archive_id=archive_id,
                        contribution=contribution,
                        stage_ids=stale_stage_ids,
                    )
                    if refreshed_stage_ids:
                        persisted_stage_ids = self._ordered_stage_ids(
                            self.runtime_repository.list_stage_snapshot_ids(archive_id, document_id)
                        )
        stage_statuses = self._infer_stage_statuses(context)
        current_stage_id = (
            context["current_stage_id"]
            if context.get("current_stage_id") in {definition.stage_id for definition in STAGE_DEFINITIONS}
            else self._select_current_stage_id(stage_statuses)
        )
        stages = [
            self._build_stage(
                definition,
                context,
                stage_statuses[definition.stage_id],
                is_current=definition.stage_id == current_stage_id,
            )
            for definition in STAGE_DEFINITIONS
        ]
        current_stage = next((stage for stage in stages if stage.is_current), stages[-1])
        rule_execution_records = [
            record
            for stage in stages
            for record in stage.rule_execution_records
        ]
        policy_refs = self._policy_refs(context.get("policy_snapshot"))
        quality_gate_summary = self._build_quality_gate_summary(
            stages,
            context,
            rule_execution_records,
        )
        return DocumentRuntimeContract(
            archive_id=archive_id,
            document_id=document_id,
            document_title=context["document_title"],
            current_stage_id=current_stage.stage_id,
            current_stage_label=context.get("current_stage_label") or current_stage.label,
            current_stage_status=current_stage.status,
            current_stage_message=context.get("current_stage_message"),
            status=current_stage.status,
            runtime_mode=self._select_runtime_mode(used_legacy_source, persisted_stage_ids),
            persisted_stage_ids=persisted_stage_ids,
            source_document=context["source_document"],
            policy_snapshot=context.get("policy_snapshot"),
            policy_package_id=policy_refs.get("policy_package_id"),
            policy_version=policy_refs.get("policy_version"),
            policy_snapshot_id=policy_refs.get("policy_snapshot_id"),
            stage_statuses={stage.stage_id: stage.status.value for stage in stages},
            rule_hits=quality_gate_summary.get("rule_hits", []),
            quality_gate=quality_gate_summary,
            publication_candidate_status=self._build_publication_candidate_status(stages),
            stages=stages,
            rule_execution_records=rule_execution_records,
        ).model_dump(mode="json")

    def _persisted_snapshots_requiring_refresh(
        self,
        archive_id: str,
        document_id: str,
        persisted_stage_ids: list[str],
    ) -> list[str]:
        stale_stage_ids: list[str] = []
        for stage_id in persisted_stage_ids:
            snapshot = self.runtime_repository.load_stage_snapshot(archive_id, document_id, stage_id)
            if snapshot is None:
                stale_stage_ids.append(stage_id)
                continue
            if int(snapshot.get("snapshot_contract_version") or 0) < RUNTIME_SNAPSHOT_CONTRACT_VERSION:
                stale_stage_ids.append(stage_id)
                continue
            if stage_id == "indexes_snapshots_apis" and self._publication_snapshot_needs_refresh(
                archive_id,
                document_id,
                snapshot,
            ):
                stale_stage_ids.append(stage_id)
        return stale_stage_ids

    def _publication_snapshot_needs_refresh(
        self,
        archive_id: str,
        document_id: str,
        snapshot: dict[str, Any],
    ) -> bool:
        current_version, document_published = self.runtime_snapshot_service._build_publication_context(
            archive_id,
            document_id,
        )
        fields = self._extract_observer_fields(snapshot)
        formally_admitted = document_published and bool(current_version)
        expected_formal_entry = "已正式入库" if formally_admitted else "尚未正式入库"
        expected_governance = "治理已确认" if formally_admitted else None
        expected_version = (current_version or {}).get("version_label")
        expected_review_counts = self._load_document_review_counts(archive_id, document_id)

        if fields.get("formal_entry_status") != expected_formal_entry:
            return True
        if expected_governance and fields.get("governance_confirmation_status") != expected_governance:
            return True
        if expected_version and fields.get("version_label") != expected_version:
            return True
        if not expected_version and fields.get("formal_entry_status") == "已正式入库":
            return True
        if expected_review_counts is not None:
            if fields.get("pending_review_count") != str(expected_review_counts["pending_count"]):
                return True
            if fields.get("approved_count") != str(expected_review_counts["approved_count"]):
                return True
            if fields.get("rejected_count") != str(expected_review_counts["rejected_count"]):
                return True
        return False

    @staticmethod
    def _extract_observer_fields(snapshot: dict[str, Any]) -> dict[str, Any]:
        stage_observer = snapshot.get("stage_observer") or {}
        fields: dict[str, Any] = {}
        for section in stage_observer.get("sections", []):
            for field in section.get("fields", []):
                key = field.get("key")
                if key:
                    fields[key] = field.get("value")
        return fields

    def _load_document_review_counts(self, archive_id: str, document_id: str) -> dict[str, int] | None:
        try:
            payload = self.knowledge_service._load_raw(archive_id)
        except FileNotFoundError:
            return None
        document_index = self.knowledge_service._build_document_index(payload)
        document = document_index.get(document_id)
        if document is None:
            return None
        knowledge_items = self.knowledge_service._build_document_knowledge_items(payload, document_id, document)
        return {
            "pending_count": sum(1 for item in knowledge_items if item.get("review_status", "pending") == "pending"),
            "approved_count": sum(1 for item in knowledge_items if item.get("review_status") == "approved"),
            "rejected_count": sum(1 for item in knowledge_items if item.get("review_status") == "rejected"),
        }

    def _load_build_state_document_source(self, build_state: dict[str, Any], document_id: str) -> dict[str, Any] | None:
        for document in build_state.get("documents", []):
            if document.get("document_id") != document_id:
                continue
            return {
                "document_id": document.get("document_id"),
                "title": document.get("title"),
                "path": document.get("path"),
                "file_type": document.get("file_type"),
                "source_archive": document.get("source_archive"),
                "source_file_path": document.get("source_file_path"),
                "source_digest": document.get("source_digest"),
                "included_in_archive": document.get("included_in_archive", True),
                "parser_name": document.get("parser_name"),
                "segment_count": document.get("segment_count", 0),
                "character_count": document.get("character_count", 0),
            }
        return None

    def _load_legacy_document_runtime_source(self, archive_id: str, document_id: str) -> dict[str, Any] | None:
        try:
            payload = self.knowledge_service._load_public(archive_id)
        except FileNotFoundError:
            return None
        document_index = self.knowledge_service._build_document_index(payload)
        document = document_index.get(document_id)
        if document is None:
            return None

        filtered_payload = self.knowledge_service._apply_document_filter(payload, [document_id])
        contribution = {
            "document": {
                "id": document["id"],
                "path": document.get("path"),
                "title": document["title"],
                "file_type": document["file_type"],
                "source_archive": document["source_archive"],
                "character_count": document["character_count"],
                "parser_name": document.get("parser_name"),
                "segment_count": document.get("segment_count", 0),
                "source_file_path": document.get("path"),
                "source_digest": None,
            },
            "entities": filtered_payload.get("entities", []),
            "events": filtered_payload.get("events", []),
            "processes": filtered_payload.get("processes", []),
            "relations": filtered_payload.get("relations", []),
            "extraction": {
                "strategy": "legacy_archive_mapping",
                "schema_version": "legacy",
                "candidate_count": (
                    len(filtered_payload.get("entities", []))
                    + len(filtered_payload.get("events", []))
                    + len(filtered_payload.get("processes", []))
                ),
                "relation_count": len(filtered_payload.get("relations", [])),
                "derived": True,
            },
        }
        document_source = {
            "document_id": document["id"],
            "title": document["title"],
            "path": document.get("path"),
            "file_type": document["file_type"],
            "source_archive": document["source_archive"],
            "character_count": document["character_count"],
            "included_in_archive": True,
            "parser_name": document.get("parser_name"),
            "segment_count": document.get("segment_count", 0),
            "source_file_path": document.get("path"),
            "source_digest": None,
        }
        return {
            "document_source": document_source,
            "contribution": contribution,
        }

    def _build_context(
        self,
        *,
        archive_id: str,
        document_id: str,
        document: dict,
        document_source: dict,
        contribution: dict,
        build_state: dict,
        publication: dict,
    ) -> dict[str, Any]:
        entities = contribution.get("entities", [])
        events = contribution.get("events", [])
        processes = contribution.get("processes", [])
        relations = contribution.get("relations", [])
        all_items = (
            [{"kind": "entity", **item} for item in entities]
            + [{"kind": "event", **item} for item in events]
            + [{"kind": "process", **item} for item in processes]
        )
        evidence = [entry for item in all_items for entry in item.get("evidence", [])]
        extraction = contribution.get("extraction", {})
        is_current_build_document = build_state.get("current_document_id") == document_id and build_state.get("status") == "running"
        return {
            "archive_id": archive_id,
            "document_id": document_id,
            "document_title": document.get("title") or document_source.get("title") or document_id,
            "document_path": document.get("path") or document_source.get("path"),
            "document_file_type": document.get("file_type") or document_source.get("file_type"),
            "document_character_count": document.get("character_count") or document_source.get("character_count") or 0,
            "source_document": {
                "title": document.get("title") or document_source.get("title"),
                "path": document.get("path") or document_source.get("path"),
                "file_type": document.get("file_type") or document_source.get("file_type"),
                "source_archive": document.get("source_archive") or document_source.get("source_archive"),
                "source_file_path": document.get("source_file_path") or document_source.get("source_file_path"),
                "source_digest": document.get("source_digest") or document_source.get("source_digest"),
                "parser_name": document.get("parser_name") or document_source.get("parser_name"),
                "segment_count": document.get("segment_count") or document_source.get("segment_count") or 0,
                "included_in_archive": document_source.get("included_in_archive", True),
            },
            "entities": entities,
            "events": events,
            "processes": processes,
            "relations": relations,
            "all_items": all_items,
            "evidence": evidence,
            "extraction": extraction,
            "publication": publication,
            "published_current_version": publication.get("current_version"),
            "is_current_build_document": is_current_build_document,
            "current_chunk": build_state.get("current_chunk") if is_current_build_document else None,
            "build_warnings": build_state.get("warnings", []) if is_current_build_document else [],
            "build_state": build_state,
            "policy_snapshot": build_state.get("policy_snapshot"),
            "current_stage_id": build_state.get("current_stage_id") if is_current_build_document else None,
            "current_stage_label": build_state.get("current_stage_label") if is_current_build_document else None,
            "current_stage_status": build_state.get("current_stage_status") if is_current_build_document else None,
            "current_stage_message": build_state.get("current_stage_message") if is_current_build_document else None,
        }

    def _ordered_stage_ids(self, stage_ids: list[str]) -> list[str]:
        known = {definition.stage_id: definition.order for definition in STAGE_DEFINITIONS}
        return sorted(stage_ids, key=lambda stage_id: (known.get(stage_id, 999), stage_id))

    def _select_runtime_mode(self, used_legacy_source: bool, persisted_stage_ids: list[str]) -> str:
        if used_legacy_source and not persisted_stage_ids:
            return "legacy_fallback"
        if len(persisted_stage_ids) == len(STAGE_DEFINITIONS):
            return "persisted"
        if persisted_stage_ids:
            return "hybrid"
        return "derived"

    def _normalize_policy_snapshot(
        self,
        policy_snapshot: Any,
        *,
        archive_id: str,
        persisted_stage_ids: list[str],
        document_id: str,
    ) -> dict[str, Any] | None:
        if isinstance(policy_snapshot, dict):
            normalized = dict(policy_snapshot)
        else:
            normalized = self._derive_policy_snapshot_from_stage_refs(
                archive_id=archive_id,
                document_id=document_id,
                persisted_stage_ids=persisted_stage_ids,
            )
            if normalized is None:
                return None

        snapshot_id = normalized.get("policy_snapshot_id") or normalized.get("snapshot_id")
        policy_version = (
            normalized.get("policy_version")
            or normalized.get("policy_package_version_id")
            or normalized.get("version_label")
        )
        if snapshot_id:
            normalized["snapshot_id"] = str(normalized.get("snapshot_id") or snapshot_id)
            normalized["policy_snapshot_id"] = str(snapshot_id)
        if policy_version:
            normalized["policy_version"] = str(policy_version)
        return normalized

    def _derive_policy_snapshot_from_stage_refs(
        self,
        *,
        archive_id: str,
        document_id: str,
        persisted_stage_ids: list[str],
    ) -> dict[str, Any] | None:
        for stage_id in persisted_stage_ids:
            snapshot = self.runtime_repository.load_stage_snapshot(archive_id, document_id, stage_id)
            if not isinstance(snapshot, dict):
                continue
            policy_snapshot_id = snapshot.get("policy_snapshot_id")
            policy_package_id = snapshot.get("policy_package_id")
            policy_version = snapshot.get("policy_version")
            if not (policy_snapshot_id or policy_package_id or policy_version):
                continue
            return {
                "snapshot_id": str(policy_snapshot_id or "unknown-policy-snapshot"),
                "policy_snapshot_id": str(policy_snapshot_id or "unknown-policy-snapshot"),
                "archive_id": archive_id,
                "policy_package_id": str(policy_package_id) if policy_package_id else None,
                "policy_version": str(policy_version or "unknown-policy-version"),
                "version_label": str(policy_version or "unknown-policy-version"),
                "scope_label": "persisted runtime snapshot",
                "stage_order": [],
                "stages": [],
            }
        return None

    @staticmethod
    def _policy_refs(policy_snapshot: Any) -> dict[str, str | None]:
        if not isinstance(policy_snapshot, dict):
            return {"policy_package_id": None, "policy_version": None, "policy_snapshot_id": None}
        return {
            "policy_package_id": (
                str(policy_snapshot.get("policy_package_id"))
                if policy_snapshot.get("policy_package_id")
                else None
            ),
            "policy_version": (
                str(
                    policy_snapshot.get("policy_version")
                    or policy_snapshot.get("policy_package_version_id")
                    or policy_snapshot.get("version_label")
                )
                if (
                    policy_snapshot.get("policy_version")
                    or policy_snapshot.get("policy_package_version_id")
                    or policy_snapshot.get("version_label")
                )
                else None
            ),
            "policy_snapshot_id": (
                str(policy_snapshot.get("policy_snapshot_id") or policy_snapshot.get("snapshot_id"))
                if (policy_snapshot.get("policy_snapshot_id") or policy_snapshot.get("snapshot_id"))
                else None
            ),
        }

    @staticmethod
    def _runtime_status_from_value(value: Any, fallback: RuntimeStatus) -> RuntimeStatus:
        try:
            return RuntimeStatus(str(value))
        except (TypeError, ValueError):
            return fallback

    def _infer_stage_statuses(self, context: dict[str, Any]) -> dict[str, RuntimeStatus]:
        statuses = {definition.stage_id: RuntimeStatus.PENDING for definition in STAGE_DEFINITIONS}
        source = context["source_document"]
        has_document = bool(context["document_path"] or source.get("source_file_path"))
        has_parser = bool(source.get("parser_name"))
        has_segments = int(source.get("segment_count") or 0) > 0
        has_evidence = bool(context["evidence"])
        has_items = bool(context["all_items"])
        has_relations = bool(context["relations"])
        has_publication = bool(context["published_current_version"])
        running_doc = context["is_current_build_document"]
        has_current_chunk = bool(context["current_chunk"])

        if has_document:
            statuses["asset_intake"] = RuntimeStatus.COMPLETED
        if has_parser:
            statuses["parser_router"] = RuntimeStatus.COMPLETED
            statuses["parser_execution"] = RuntimeStatus.COMPLETED
        if has_segments:
            statuses["unified_document_object"] = RuntimeStatus.COMPLETED
        if has_evidence:
            statuses["evidence_constructor"] = RuntimeStatus.COMPLETED
        if has_segments:
            statuses["evidence_graph_chunk_layer"] = RuntimeStatus.COMPLETED
        if context["extraction"].get("candidate_count") or context["extraction"].get("relation_count"):
            statuses["evidence_pack"] = RuntimeStatus.COMPLETED
        if has_items:
            statuses["concept_candidate_review"] = RuntimeStatus.COMPLETED
            statuses["definition_summary_conflict_consolidation"] = RuntimeStatus.WARNING
            statuses["canonical_knowledge"] = RuntimeStatus.COMPLETED
        if has_relations or any(item.get("aliases") for item in context["all_items"]):
            statuses["relation_review_family_normalization"] = RuntimeStatus.COMPLETED

        active_stage_id = context.get("current_stage_id")
        if running_doc and active_stage_id:
            active_order = next(
                (definition.order for definition in STAGE_DEFINITIONS if definition.stage_id == active_stage_id),
                None,
            )
            if active_order is not None:
                for definition in STAGE_DEFINITIONS:
                    if definition.order < active_order:
                        if statuses[definition.stage_id] == RuntimeStatus.PENDING:
                            statuses[definition.stage_id] = RuntimeStatus.COMPLETED
                    elif definition.stage_id == active_stage_id:
                        statuses[definition.stage_id] = self._runtime_status_from_value(
                            context.get("current_stage_status"),
                            RuntimeStatus.RUNNING,
                        )
                    else:
                        statuses[definition.stage_id] = RuntimeStatus.PENDING
                return statuses

        if running_doc and has_current_chunk:
            statuses["evidence_graph_chunk_layer"] = RuntimeStatus.RUNNING
            for stage_id in (
                "evidence_pack",
                "concept_candidate_review",
                "relation_review_family_normalization",
                "definition_summary_conflict_consolidation",
                "canonical_knowledge",
                "quality_policy_evaluation_governance_gate",
                "indexes_snapshots_apis",
            ):
                statuses[stage_id] = RuntimeStatus.PENDING
            return statuses

        if has_items:
            statuses["quality_policy_evaluation_governance_gate"] = RuntimeStatus.RUNNING
        if has_publication:
            # Once a formal version exists, the earlier definition warning should no longer
            # outrank the terminal publication stage as the "current" runtime location.
            statuses["definition_summary_conflict_consolidation"] = RuntimeStatus.COMPLETED
            statuses["quality_policy_evaluation_governance_gate"] = RuntimeStatus.COMPLETED
            statuses["indexes_snapshots_apis"] = RuntimeStatus.COMPLETED
        return statuses

    def _build_stage(
        self,
        definition: RuntimeStageDefinition,
        context: dict[str, Any],
        status: RuntimeStatus,
        *,
        is_current: bool,
    ) -> RuntimeStageSnapshot:
        persisted = self.runtime_repository.load_stage_snapshot(
            context["archive_id"],
            context["document_id"],
            definition.stage_id,
        )
        if persisted is not None:
            stage = RuntimeStageSnapshot.model_validate(persisted)
            stage.is_current = is_current
            stage = self._apply_current_stage_status(stage, context, is_current=is_current)
            return self._with_policy_rule_records(stage, definition, context)
        builder = getattr(self, f"_build_{definition.stage_id}_stage")
        stage = builder(definition, context, status)
        stage.is_current = is_current
        stage = self._apply_current_stage_status(stage, context, is_current=is_current)
        return self._with_policy_rule_records(stage, definition, context)

    def _apply_current_stage_status(
        self,
        stage: RuntimeStageSnapshot,
        context: dict[str, Any],
        *,
        is_current: bool,
    ) -> RuntimeStageSnapshot:
        if not is_current or not context.get("is_current_build_document"):
            return stage
        stage_status = self._runtime_status_from_value(context.get("current_stage_status"), stage.status)
        stage.status = stage_status
        stage.stage_observer.status = stage_status
        return stage

    def _with_policy_rule_records(
        self,
        stage: RuntimeStageSnapshot,
        definition: RuntimeStageDefinition,
        context: dict[str, Any],
    ) -> RuntimeStageSnapshot:
        if stage.rule_execution_records:
            return stage
        records = self._derive_policy_rule_records(stage, definition, context)
        if records:
            stage.rule_execution_records = records
        return stage

    def _derive_policy_rule_records(
        self,
        stage: RuntimeStageSnapshot,
        definition: RuntimeStageDefinition,
        context: dict[str, Any],
    ) -> list[RuleExecutionRecord]:
        policy_snapshot = context.get("policy_snapshot")
        if not isinstance(policy_snapshot, dict):
            return []
        policy_stage = next(
            (
                item
                for item in policy_snapshot.get("stages", [])
                if isinstance(item, dict) and item.get("stage_id") == definition.stage_id
            ),
            None,
        )
        if not isinstance(policy_stage, dict):
            return []
        rules = [rule for rule in policy_stage.get("rules", []) if isinstance(rule, dict)]
        if not rules:
            return []

        policy_refs = self._policy_refs(policy_snapshot)
        snapshot_id = str(policy_refs.get("policy_snapshot_id") or policy_snapshot.get("snapshot_id") or "")
        affected_object_ids = stage.graph.primary_node_ids or [node.node_id for node in stage.graph.nodes[:8]]
        records: list[RuleExecutionRecord] = []
        for index, rule in enumerate(rules, start=1):
            rule_id = str(rule.get("rule_id") or rule.get("key") or f"{definition.stage_id}-rule-{index}")
            rule_version = str(rule.get("rule_version") or "r1.0")
            input_refs = self._schema_artifact_refs(rule.get("input_schema"), "source_artifact", [f"{definition.stage_id}.input"])
            output_refs = self._schema_artifact_refs(rule.get("output_schema"), "target_artifact", [f"{definition.stage_id}.output"])
            input_payload = {
                "snapshot_id": snapshot_id,
                "archive_id": context["archive_id"],
                "document_id": context["document_id"],
                "stage_id": definition.stage_id,
                "rule_id": rule_id,
                "rule_version": rule_version,
                "input_artifact_refs": input_refs,
            }
            output_payload = {
                "stage_status": stage.status.value,
                "rule_id": rule_id,
                "affected_object_ids": affected_object_ids,
                "output_artifact_refs": output_refs,
            }
            records.append(
                RuleExecutionRecord(
                    execution_id=f"rex-{context['document_id']}-{definition.stage_id}-{rule_id}",
                    archive_id=context["archive_id"],
                    document_id=context["document_id"],
                    stage_id=definition.stage_id,
                    rule_id=rule_id,
                    rule_version=rule_version,
                    rule_hash=rule.get("rule_hash"),
                    snapshot_id=snapshot_id or None,
                    policy_snapshot_id=snapshot_id or None,
                    policy_package_id=policy_refs.get("policy_package_id"),
                    policy_version=policy_refs.get("policy_version"),
                    input_artifact_refs=input_refs,
                    input_hash=self._runtime_hash(input_payload),
                    output_artifact_refs=output_refs,
                    output_hash=self._runtime_hash(output_payload),
                    affected_object_ids=affected_object_ids,
                    affected_relation_ids=[],
                    decision="not_started" if stage.status == RuntimeStatus.PENDING else str(rule.get("effect_kind") or rule.get("action") or stage.status.value),
                    metrics={
                        "stage_status": stage.status.value,
                        "threshold": rule.get("threshold"),
                        "contract_status": rule.get("contract_status"),
                    },
                    executed_at=policy_snapshot.get("captured_at"),
                    source="policy_snapshot",
                )
            )
        return records

    @staticmethod
    def _runtime_hash(payload: Any) -> str:
        normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return "sha256:" + sha256(normalized.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _schema_artifact_refs(schema: Any, key: str, fallback: list[str]) -> list[str]:
        if not isinstance(schema, list):
            return fallback
        refs: list[str] = []
        for field in schema:
            if not isinstance(field, dict):
                continue
            value = field.get(key)
            if value is not None and str(value) and str(value) not in refs:
                refs.append(str(value))
        return refs or fallback

    def _build_quality_gate_summary(
        self,
        stages: list[RuntimeStageSnapshot],
        context: dict[str, Any],
        rule_execution_records: list[RuleExecutionRecord],
    ) -> dict[str, Any]:
        stage = next(
            (
                item
                for item in stages
                if item.stage_id == "quality_policy_evaluation_governance_gate"
            ),
            None,
        )
        policy_refs = self._policy_refs(context.get("policy_snapshot"))
        if stage is None:
            return {
                "stage_id": "quality_policy_evaluation_governance_gate",
                "stage_status": RuntimeStatus.UNAVAILABLE.value,
                "policy": policy_refs,
                "metrics": {},
                "rule_hits": [],
                "decision": {},
                "rule_execution_records": [],
            }

        fields = self._observer_payload_fields(stage.stage_observer)
        rule_hits = self._rule_hits_from_quality_gate_stage(stage)
        gate_node = next(
            (
                node
                for node in stage.graph.nodes
                if node.node_type == "gate_decision"
            ),
            None,
        )
        decision = {
            "status": fields.get("decision") or (gate_node.attributes.get("decision") if gate_node else stage.status.value),
            "reason": fields.get("reason") or (gate_node.attributes.get("reason") if gate_node else None),
            "next_action": gate_node.attributes.get("next_action") if gate_node else None,
            "failed_rule_count": fields.get("failed_rule_count")
            or (gate_node.metrics.get("failed_rule_count") if gate_node else None),
        }
        metrics = {}
        if gate_node:
            metrics.update(gate_node.metrics)
        metrics.update(
            {
                key: value
                for key, value in fields.items()
                if key
                in {
                    "knowledge_item_count",
                    "evidence_count",
                    "supporting_documents",
                    "pending_review_count",
                    "rejected_count",
                    "approved_count",
                    "hard_conflict",
                    "risk_score",
                    "failed_rule_count",
                }
            }
        )
        policy = {
            **policy_refs,
            "stage_id": stage.stage_id,
            "stage_label": stage.label,
            "rule_count": len(rule_hits),
            "default_action": fields.get("default_action"),
        }
        stage_records = [
            record.model_dump(mode="json")
            for record in rule_execution_records
            if record.stage_id == stage.stage_id
        ]
        return {
            "stage_id": stage.stage_id,
            "stage_label": stage.label,
            "stage_status": stage.status.value,
            "policy": policy,
            "metrics": metrics,
            "rule_hits": rule_hits,
            "decision": decision,
            "rule_execution_records": stage_records,
        }

    @staticmethod
    def _observer_payload_fields(observer: RuntimeObserverPayload) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        for section in observer.sections:
            for field in section.fields:
                fields[field.key] = field.value
        return fields

    @staticmethod
    def _rule_hits_from_quality_gate_stage(stage: RuntimeStageSnapshot) -> list[dict[str, Any]]:
        hits: list[dict[str, Any]] = []
        for node in stage.graph.nodes:
            if node.node_type != "rule_hit":
                continue
            attrs = node.attributes
            metrics = node.metrics
            hits.append(
                {
                    "node_id": node.node_id,
                    "rule_key": attrs.get("rule_key"),
                    "rule_id": attrs.get("rule_id") or attrs.get("rule_key"),
                    "rule_version": attrs.get("rule_version"),
                    "rule_hash": attrs.get("rule_hash"),
                    "snapshot_id": attrs.get("snapshot_id"),
                    "input_hash": attrs.get("input_hash"),
                    "output_hash": attrs.get("output_hash"),
                    "label": node.label,
                    "status": node.status.value,
                    "threshold": attrs.get("threshold"),
                    "action": attrs.get("action"),
                    "outcome": attrs.get("outcome"),
                    "actual": metrics.get("actual"),
                    "passed": bool(metrics.get("passed")),
                    "detail": attrs.get("detail"),
                    "affected_object_ids": attrs.get("affected_object_ids", []),
                }
            )
        return hits

    def _build_publication_candidate_status(
        self,
        stages: list[RuntimeStageSnapshot],
    ) -> dict[str, Any]:
        stage = next((item for item in stages if item.stage_id == "indexes_snapshots_apis"), None)
        if stage is None:
            return {}
        fields = self._observer_payload_fields(stage.stage_observer)
        candidate_node = next(
            (
                node
                for node in stage.graph.nodes
                if node.node_type == "publication_candidate_snapshot"
            ),
            None,
        )
        return {
            "stage_id": stage.stage_id,
            "stage_status": stage.status.value,
            "gate_decision": fields.get("gate_decision"),
            "machine_candidate_status": fields.get("machine_candidate_status"),
            "governance_confirmation_status": fields.get("governance_confirmation_status"),
            "formal_entry_status": fields.get("formal_entry_status"),
            "version_label": fields.get("version_label"),
            "candidate_count": fields.get("candidate_count"),
            "pending_review_count": fields.get("pending_review_count"),
            "approved_count": fields.get("approved_count"),
            "rejected_count": fields.get("rejected_count"),
            "candidate_snapshot_id": candidate_node.node_id if candidate_node else None,
            "candidate_snapshot_attributes": candidate_node.attributes if candidate_node else {},
        }

    def _select_current_stage_id(self, statuses: dict[str, RuntimeStatus]) -> str:
        for preferred in (RuntimeStatus.RUNNING, RuntimeStatus.BLOCKED, RuntimeStatus.WARNING):
            for definition in reversed(STAGE_DEFINITIONS):
                if statuses[definition.stage_id] == preferred:
                    return definition.stage_id
        for definition in reversed(STAGE_DEFINITIONS):
            if statuses[definition.stage_id] == RuntimeStatus.COMPLETED:
                return definition.stage_id
        return STAGE_DEFINITIONS[0].stage_id

    def _stage_snapshot(
        self,
        definition: RuntimeStageDefinition,
        status: RuntimeStatus,
        nodes: list[RuntimeGraphNode],
        edges: list[RuntimeGraphEdge],
        stage_observer: RuntimeObserverPayload,
        node_observers: dict[str, RuntimeObserverPayload],
        edge_observers: dict[str, RuntimeObserverPayload],
    ) -> RuntimeStageSnapshot:
        return RuntimeStageSnapshot(
            stage_id=definition.stage_id,
            label=definition.label,
            group=definition.group,
            order=definition.order,
            status=status,
            graph=RuntimeStageGraph(
                nodes=nodes,
                edges=edges,
                primary_node_ids=[node.node_id for node in nodes if node.is_primary],
                primary_edge_ids=[edge.edge_id for edge in edges if edge.is_primary],
            ),
            stage_observer=stage_observer,
            node_observers=node_observers,
            edge_observers=edge_observers,
        )

    def _node(
        self,
        node_id: str,
        label: str,
        node_type: str,
        stage_id: str,
        status: RuntimeStatus,
        is_primary: bool = False,
        *,
        origin: RuntimeOrigin = RuntimeOrigin.SOURCE,
        attributes: dict[str, Any] | None = None,
    ) -> RuntimeGraphNode:
        return RuntimeGraphNode(
            node_id=node_id,
            label=label,
            node_type=node_type,
            stage_id=stage_id,
            status=status,
            origin=origin,
            is_primary=is_primary,
            attributes=attributes or {},
        )

    def _edge(
        self,
        edge_id: str,
        source: str,
        target: str,
        relation: str,
        stage_id: str,
        status: RuntimeStatus,
        is_primary: bool = False,
        *,
        origin: RuntimeOrigin = RuntimeOrigin.SOURCE,
        attributes: dict[str, Any] | None = None,
    ) -> RuntimeGraphEdge:
        return RuntimeGraphEdge(
            edge_id=edge_id,
            source=source,
            target=target,
            relation=relation,
            stage_id=stage_id,
            status=status,
            origin=origin,
            is_primary=is_primary,
            attributes=attributes or {},
        )

    def _observer_stage(
        self,
        *,
        title: str,
        subtitle: str,
        status: RuntimeStatus,
        stream: list[RuntimeEvent],
        sections: list[RuntimeSummarySection],
        actions: list[RuntimeAction] | None = None,
    ) -> RuntimeObserverPayload:
        return RuntimeObserverPayload(
            mode=RuntimeObserverMode.STAGE,
            title=title,
            subtitle=subtitle,
            status=status,
            stream=stream,
            sections=sections,
            actions=actions
            or [RuntimeAction(action_id="view-stage-graph", label="查看阶段图谱", target_kind="graph")],
        )

    def _observer_node(
        self,
        title: str,
        subtitle: str,
        status: RuntimeStatus,
        stream: list[RuntimeEvent],
        sections: list[RuntimeSummarySection],
    ) -> RuntimeObserverPayload:
        return RuntimeObserverPayload(
            mode=RuntimeObserverMode.NODE,
            title=title,
            subtitle=subtitle,
            status=status,
            stream=stream,
            sections=sections,
            actions=[
                RuntimeAction(action_id="view-upstream", label="查看上游对象", target_kind="graph"),
                RuntimeAction(action_id="view-evidence", label="查看证据", target_kind="evidence"),
            ],
        )

    def _observer_edge(
        self,
        title: str,
        subtitle: str,
        status: RuntimeStatus,
        stream: list[RuntimeEvent],
        sections: list[RuntimeSummarySection],
    ) -> RuntimeObserverPayload:
        return RuntimeObserverPayload(
            mode=RuntimeObserverMode.EDGE,
            title=title,
            subtitle=subtitle,
            status=status,
            stream=stream,
            sections=sections,
            actions=[
                RuntimeAction(action_id="view-source-node", label="查看源节点", target_kind="node"),
                RuntimeAction(action_id="view-target-node", label="查看目标节点", target_kind="node"),
            ],
        )

    def _event(
        self,
        kind: str,
        message: str,
        *,
        level: str = "info",
        timestamp: str | None = None,
    ) -> RuntimeEvent:
        return RuntimeEvent(
            event_id=f"{kind}:{abs(hash((kind, message))) % 999999}",
            kind=kind,  # type: ignore[arg-type]
            level=level,  # type: ignore[arg-type]
            message=message,
            timestamp=timestamp,
        )

    def _section(self, section_id: str, title: str, rows: list[tuple[str, str]]) -> RuntimeSummarySection:
        return RuntimeSummarySection(
            section_id=section_id,
            title=title,
            fields=[RuntimeSummaryField(key=key, label=key, value=value) for key, value in rows],
        )

    def _build_asset_intake_stage(self, definition, context, status):
        source = context["source_document"]
        file_id = f"{context['document_id']}:source-file"
        directory_id = f"{context['document_id']}:source-dir"
        digest_id = f"{context['document_id']}:digest"
        result_id = f"{context['document_id']}:intake-result"
        nodes = [
            self._node(file_id, "源文件", "source_file", definition.stage_id, status, True, attributes={"title": context["document_title"], "path": source.get("source_file_path") or context["document_path"], "file_type": context["document_file_type"]}),
            self._node(directory_id, "源目录", "source_directory", definition.stage_id, RuntimeStatus.COMPLETED, attributes={"path": context["document_path"]}),
            self._node(digest_id, "摘要校验", "file_digest", definition.stage_id, RuntimeStatus.COMPLETED if source.get("source_digest") else RuntimeStatus.UNAVAILABLE, origin=RuntimeOrigin.DERIVED, attributes={"source_digest": source.get("source_digest")}),
            self._node(result_id, "接入结果", "intake_result", definition.stage_id, status, origin=RuntimeOrigin.DERIVED, attributes={"included_in_archive": source.get("included_in_archive", True)}),
        ]
        edges = [
            self._edge(f"{file_id}:located", file_id, directory_id, "located_in", definition.stage_id, RuntimeStatus.COMPLETED, True),
            self._edge(f"{file_id}:digest", file_id, digest_id, "hashed_to", definition.stage_id, RuntimeStatus.COMPLETED if source.get("source_digest") else RuntimeStatus.UNAVAILABLE, True),
            self._edge(f"{file_id}:result", file_id, result_id, "results_in", definition.stage_id, status, True),
        ]
        return self._stage_snapshot(
            definition,
            status,
            nodes,
            edges,
            self._observer_stage(
                title="阶段视角 · 素材接入",
                subtitle=context["document_title"],
                status=status,
                stream=[
                    self._event("progress", f"发现源文件：{context['document_title']}"),
                    self._event("result", f"文件类型识别为 {context['document_file_type'] or 'unknown'}"),
                    self._event("result", "摘要校验已完成" if source.get("source_digest") else "尚未产出摘要校验结果"),
                ],
                sections=[
                    self._section("input", "输入摘要", [("源文件", context["document_title"]), ("源路径", source.get("source_file_path") or context["document_path"] or "未记录")]),
                    self._section("output", "输出摘要", [("接入状态", "已接入"), ("归档纳入", "是" if source.get("included_in_archive", True) else "否")]),
                ],
            ),
            {
                file_id: self._observer_node("节点视角 · 源文件", "当前接入的原始文档文件。", status, [self._event("info", f"文件标题：{context['document_title']}")], [self._section("identity", "对象身份", [("文件类型", context["document_file_type"] or "unknown"), ("源路径", source.get("source_file_path") or context["document_path"] or "未记录")]), self._section("trace", "追溯信息", [("摘要值", source.get("source_digest") or "未记录"), ("归档", source.get("source_archive") or "未记录")])]),
                digest_id: self._observer_node("节点视角 · 摘要校验", "用于判定文件唯一性和复用能力。", RuntimeStatus.COMPLETED if source.get("source_digest") else RuntimeStatus.UNAVAILABLE, [self._event("result", "摘要值已写入接入记录" if source.get("source_digest") else "当前文件未记录摘要")], [self._section("digest", "摘要信息", [("source_digest", source.get("source_digest") or "未记录")])]),
                result_id: self._observer_node("节点视角 · 接入结果", "接入阶段对该文档形成的结果对象。", status, [self._event("result", "文档已纳入单文档处理链入口")], [self._section("result", "结果摘要", [("纳入知识库", "是" if source.get("included_in_archive", True) else "否")])]),
            },
            {
                f"{file_id}:result": self._observer_edge("边视角 · results_in", "说明源文件如何形成接入结果。", status, [self._event("result", "源文件通过接入校验后形成接入结果对象")], [self._section("relation", "关系定义", [("关系类型", "results_in"), ("源对象", "源文件"), ("目标对象", "接入结果")])]),
            },
        )

    def _build_parser_router_stage(self, definition, context, status):
        source = context["source_document"]
        router_id = f"{context['document_id']}:router"
        type_id = f"{context['document_id']}:document-type"
        parser_id = f"{context['document_id']}:parser-choice"
        decision_id = f"{context['document_id']}:routing-decision"
        nodes = [
            self._node(router_id, "路由任务", "routing_task", definition.stage_id, status, True),
            self._node(type_id, "文档类型", "document_type", definition.stage_id, RuntimeStatus.COMPLETED, attributes={"file_type": context["document_file_type"]}),
            self._node(parser_id, source.get("parser_name") or "解析器未定", "parser_candidate", definition.stage_id, RuntimeStatus.COMPLETED if source.get("parser_name") else RuntimeStatus.UNAVAILABLE, attributes={"parser_name": source.get("parser_name")}),
            self._node(decision_id, "路由决策", "routing_decision", definition.stage_id, status, origin=RuntimeOrigin.DERIVED),
        ]
        edges = [
            self._edge(f"{router_id}:classified", router_id, type_id, "classified_as", definition.stage_id, RuntimeStatus.COMPLETED, True),
            self._edge(f"{router_id}:selects", router_id, parser_id, "selects", definition.stage_id, RuntimeStatus.COMPLETED if source.get("parser_name") else RuntimeStatus.UNAVAILABLE, True),
            self._edge(f"{parser_id}:decision", parser_id, decision_id, "results_in", definition.stage_id, status, True),
        ]
        return self._stage_snapshot(
            definition,
            status,
            nodes,
            edges,
            self._observer_stage(
                title="阶段视角 · 解析路由",
                subtitle=context["document_title"],
                status=status,
                stream=[self._event("progress", f"根据后缀 {context['document_file_type'] or 'unknown'} 进入解析路由"), self._event("decision", f"选择解析器：{source.get('parser_name') or '未记录'}")],
                sections=[self._section("routing", "路由摘要", [("文档类型", context["document_file_type"] or "unknown"), ("解析器", source.get("parser_name") or "未记录")])],
            ),
            {
                parser_id: self._observer_node("节点视角 · 解析器候选", "当前文档被分配到的解析器。", RuntimeStatus.COMPLETED if source.get("parser_name") else RuntimeStatus.UNAVAILABLE, [self._event("decision", f"当前选择：{source.get('parser_name') or '无'}")], [self._section("parser", "解析器信息", [("parser_name", source.get("parser_name") or "未记录")])]),
            },
            {
                f"{router_id}:selects": self._observer_edge("边视角 · selects", "路由任务如何选中解析器。", RuntimeStatus.COMPLETED if source.get("parser_name") else RuntimeStatus.UNAVAILABLE, [self._event("decision", "路由规则已选择解析器")], [self._section("relation", "关系摘要", [("关系类型", "selects"), ("结果", source.get("parser_name") or "未命中")])]),
            },
        )

    def _build_parser_execution_stage(self, definition, context, status):
        source = context["source_document"]
        parser_task = f"{context['document_id']}:parser-task"
        parsed_pages = f"{context['document_id']}:parsed-pages"
        parsed_blocks = f"{context['document_id']}:parsed-blocks"
        warning_id = f"{context['document_id']}:parse-warning"
        segment_count = int(source.get("segment_count") or 0)
        nodes = [
            self._node(parser_task, "解析任务", "parser_task", definition.stage_id, status, True, attributes={"parser_name": source.get("parser_name")}),
            self._node(parsed_pages, "解析页块集合", "parsed_page_group", definition.stage_id, RuntimeStatus.COMPLETED if segment_count else RuntimeStatus.WARNING, origin=RuntimeOrigin.DERIVED, attributes={"segment_count": segment_count}),
            self._node(parsed_blocks, "解析块集合", "parsed_block_group", definition.stage_id, RuntimeStatus.COMPLETED if segment_count else RuntimeStatus.WARNING, origin=RuntimeOrigin.DERIVED, attributes={"segment_count": segment_count}),
        ]
        edges = [
            self._edge(f"{parser_task}:pages", parser_task, parsed_pages, "parsed_to", definition.stage_id, RuntimeStatus.COMPLETED if segment_count else RuntimeStatus.WARNING, True),
            self._edge(f"{parsed_pages}:blocks", parsed_pages, parsed_blocks, "extracts", definition.stage_id, RuntimeStatus.COMPLETED if segment_count else RuntimeStatus.WARNING, True),
        ]
        if not segment_count:
            nodes.append(self._node(warning_id, "解析告警", "parsing_warning", definition.stage_id, RuntimeStatus.WARNING, attributes={"message": "未记录 segment_count，解析结构只能部分映射"}))
            edges.append(self._edge(f"{parser_task}:warning", parser_task, warning_id, "warned_by", definition.stage_id, RuntimeStatus.WARNING))
        return self._stage_snapshot(
            definition,
            status,
            nodes,
            edges,
            self._observer_stage(
                title="阶段视角 · 解析执行",
                subtitle=context["document_title"],
                status=status,
                stream=[self._event("progress", f"解析器执行：{source.get('parser_name') or '未知'}"), self._event("result", f"当前记录的段落/块数量：{segment_count}"), *([self._event("warning", "当前文档未记录完整 segment_count，解析结构为部分映射", level="warning")] if not segment_count else [])],
                sections=[self._section("parser", "执行摘要", [("parser_name", source.get("parser_name") or "未记录"), ("segment_count", str(segment_count))])],
            ),
            {
                parsed_blocks: self._observer_node("节点视角 · 解析块集合", "解析阶段产出的结构化块集合。", RuntimeStatus.COMPLETED if segment_count else RuntimeStatus.WARNING, [self._event("progress", f"已聚合 {segment_count} 个解析块")], [self._section("parsed", "块摘要", [("segment_count", str(segment_count)), ("character_count", str(context["document_character_count"]))])]),
            },
            {
                f"{parser_task}:pages": self._observer_edge("边视角 · parsed_to", "解析任务如何产出页块集合。", RuntimeStatus.COMPLETED if segment_count else RuntimeStatus.WARNING, [self._event("result", "解析任务已输出结构化页块集合")], [self._section("relation", "关系摘要", [("关系类型", "parsed_to"), ("输出规模", f"{segment_count} segments")])]),
            },
        )

    def _build_unified_document_object_stage(self, definition, context, status):
        source = context["source_document"]
        unified_doc = f"{context['document_id']}:unified-document"
        section_group = f"{context['document_id']}:unified-sections"
        paragraph_group = f"{context['document_id']}:unified-paragraphs"
        segment_count = int(source.get("segment_count") or 0)
        nodes = [
            self._node(unified_doc, "统一文档对象", "unified_document", definition.stage_id, status, True, attributes={"title": context["document_title"]}),
            self._node(section_group, "统一章节集合", "unified_section_group", definition.stage_id, RuntimeStatus.COMPLETED if segment_count else RuntimeStatus.WARNING, origin=RuntimeOrigin.DERIVED, attributes={"estimated_count": max(1, segment_count // 6) if segment_count else 0}),
            self._node(paragraph_group, "统一段落集合", "unified_paragraph_group", definition.stage_id, RuntimeStatus.COMPLETED if segment_count else RuntimeStatus.WARNING, origin=RuntimeOrigin.DERIVED, attributes={"estimated_count": segment_count}),
        ]
        edges = [
            self._edge(f"{unified_doc}:sections", unified_doc, section_group, "contains", definition.stage_id, RuntimeStatus.COMPLETED if segment_count else RuntimeStatus.WARNING, True),
            self._edge(f"{section_group}:paragraphs", section_group, paragraph_group, "contains", definition.stage_id, RuntimeStatus.COMPLETED if segment_count else RuntimeStatus.WARNING, True),
        ]
        return self._stage_snapshot(
            definition,
            status,
            nodes,
            edges,
            self._observer_stage(
                title="阶段视角 · 统一文档",
                subtitle=context["document_title"],
                status=status,
                stream=[self._event("progress", "解析块正在归并为统一文档对象"), self._event("result", f"统一结构已映射为 {segment_count} 个段落级单元")],
                sections=[self._section("unified", "统一对象摘要", [("文档标题", context["document_title"]), ("段落单元", str(segment_count))])],
            ),
            {
                unified_doc: self._observer_node("节点视角 · 统一文档对象", "解析结果收敛后的统一文档对象。", status, [self._event("result", "统一文档对象已可被后续证据阶段消费")], [self._section("identity", "对象身份", [("title", context["document_title"]), ("file_type", context["document_file_type"] or "unknown")])]),
            },
            {
                f"{section_group}:paragraphs": self._observer_edge("边视角 · contains", "统一章节如何容纳段落集合。", RuntimeStatus.COMPLETED if segment_count else RuntimeStatus.WARNING, [self._event("result", "章节与段落关系已建立")], [self._section("relation", "关系摘要", [("关系类型", "contains"), ("段落数量", str(segment_count))])]),
            },
        )

    def _build_evidence_constructor_stage(self, definition, context, status):
        evidence_units = f"{context['document_id']}:evidence-units"
        anchor_group = f"{context['document_id']}:anchors"
        evidence_count = len(context["evidence"])
        stage_status = status if status == RuntimeStatus.RUNNING else (RuntimeStatus.COMPLETED if evidence_count else RuntimeStatus.WARNING)
        nodes = [
            self._node(evidence_units, "证据单元集合", "evidence_unit_group", definition.stage_id, stage_status, True, attributes={"evidence_count": evidence_count}),
            self._node(anchor_group, "证据锚点集合", "evidence_anchor_group", definition.stage_id, stage_status, origin=RuntimeOrigin.DERIVED, attributes={"anchor_count": evidence_count}),
        ]
        edges = [self._edge(f"{evidence_units}:anchors", evidence_units, anchor_group, "anchored_at", definition.stage_id, stage_status, True)]
        return self._stage_snapshot(
            definition,
            stage_status,
            nodes,
            edges,
            self._observer_stage(
                title="阶段视角 · 证据构造",
                subtitle=context["document_title"],
                status=stage_status,
                stream=[self._event("progress", "统一文档对象正在拆解为可追溯证据单元"), self._event("result", f"当前 evidence excerpt 数量：{evidence_count}")],
                sections=[self._section("evidence", "证据摘要", [("evidence_count", str(evidence_count))])],
            ),
            {
                evidence_units: self._observer_node("节点视角 · 证据单元集合", "证据构造阶段的核心产物。", stage_status, [self._event("result", f"已生成 {evidence_count} 个证据单元")], [self._section("identity", "对象身份", [("evidence_count", str(evidence_count)), ("traceable", "是" if evidence_count else "否")])]),
            },
            {
                f"{evidence_units}:anchors": self._observer_edge("边视角 · anchored_at", "证据单元如何绑定到文档锚点。", stage_status, [self._event("result", "证据单元已绑定锚点")], [self._section("relation", "关系摘要", [("关系类型", "anchored_at"), ("锚点数量", str(evidence_count))])]),
            },
        )

    def _build_evidence_graph_chunk_layer_stage(self, definition, context, status):
        chunk_group = f"{context['document_id']}:chunk-group"
        graph_group = f"{context['document_id']}:evidence-graph"
        current_chunk = context.get("current_chunk")
        chunk_status = RuntimeStatus.RUNNING if context["is_current_build_document"] and current_chunk else status
        chunk_count = int(context["extraction"].get("candidate_count", 0)) or int(context["source_document"].get("segment_count") or 0)
        nodes = [
            self._node(chunk_group, "切块集合", "chunk_group", definition.stage_id, chunk_status, True, origin=RuntimeOrigin.DERIVED, attributes={"estimated_chunk_count": chunk_count}),
            self._node(graph_group, "证据图谱层", "evidence_graph_layer", definition.stage_id, RuntimeStatus.COMPLETED if chunk_count else RuntimeStatus.WARNING, origin=RuntimeOrigin.DERIVED, attributes={"estimated_links": max(chunk_count - 1, 0)}),
        ]
        edges = [self._edge(f"{chunk_group}:graph", chunk_group, graph_group, "connects", definition.stage_id, chunk_status, True)]
        if current_chunk:
            active_chunk_id = f"{context['document_id']}:current-chunk"
            nodes.append(self._node(active_chunk_id, "当前切块", "chunk", definition.stage_id, RuntimeStatus.RUNNING, attributes=current_chunk))
            edges.append(self._edge(f"{chunk_group}:active", chunk_group, active_chunk_id, "contains", definition.stage_id, RuntimeStatus.RUNNING))
        return self._stage_snapshot(
            definition,
            chunk_status,
            nodes,
            edges,
            self._observer_stage(
                title="阶段视角 · 证据图谱/切块",
                subtitle=context["document_title"],
                status=chunk_status,
                stream=[self._event("progress", "证据单元正在聚合为切块与图谱层"), *([self._event("progress", f"当前处理 chunk {current_chunk.get('position')}/{current_chunk.get('total')}")] if current_chunk else [])],
                sections=[self._section("chunk", "切块摘要", [("estimated_chunk_count", str(chunk_count)), ("current_chunk", current_chunk.get("chunk_id") if current_chunk else "无")])],
            ),
            {
                chunk_group: self._observer_node("节点视角 · 切块集合", "证据图谱/切块阶段的聚合对象。", chunk_status, [self._event("progress", f"预计切块数：{chunk_count}")], [self._section("chunk", "切块信息", [("estimated_chunk_count", str(chunk_count))])]),
            },
            {
                f"{chunk_group}:graph": self._observer_edge("边视角 · connects", "切块集合如何连接成证据图谱层。", chunk_status, [self._event("result", "切块之间正在建立关系连接")], [self._section("relation", "关系摘要", [("关系类型", "connects"), ("当前状态", chunk_status.value)])]),
            },
        )

    def _build_evidence_pack_stage(self, definition, context, status):
        pack_id = f"{context['document_id']}:evidence-pack"
        retrieval_id = f"{context['document_id']}:retrieval-query"
        rerank_id = f"{context['document_id']}:rerank"
        evidence_count = len(context["evidence"])
        nodes = [
            self._node(pack_id, "证据包", "evidence_pack", definition.stage_id, status, True, origin=RuntimeOrigin.DERIVED, attributes={"selected_evidence_count": evidence_count}),
            self._node(retrieval_id, "检索请求", "retrieval_query", definition.stage_id, RuntimeStatus.COMPLETED if evidence_count else RuntimeStatus.WARNING, origin=RuntimeOrigin.DERIVED),
            self._node(rerank_id, "重排结果", "rerank_result", definition.stage_id, RuntimeStatus.COMPLETED if evidence_count else RuntimeStatus.WARNING, origin=RuntimeOrigin.DERIVED, attributes={"top_k": min(evidence_count, 5)}),
        ]
        edges = [
            self._edge(f"{retrieval_id}:pack", retrieval_id, pack_id, "selected_into", definition.stage_id, status, True),
            self._edge(f"{pack_id}:rerank", pack_id, rerank_id, "reranked_to", definition.stage_id, status, True),
        ]
        return self._stage_snapshot(
            definition,
            status if evidence_count else RuntimeStatus.WARNING,
            nodes,
            edges,
            self._observer_stage(
                title="阶段视角 · 证据包",
                subtitle=context["document_title"],
                status=status if evidence_count else RuntimeStatus.WARNING,
                stream=[self._event("progress", "系统从切块层检索并组成证据包"), self._event("result", f"当前入包证据数：{evidence_count}")],
                sections=[self._section("pack", "证据包摘要", [("selected_evidence_count", str(evidence_count)), ("top_k", str(min(evidence_count, 5)))])],
            ),
            {
                pack_id: self._observer_node("节点视角 · 证据包", "当前阶段提交给知识生成子阶段的证据包。", status if evidence_count else RuntimeStatus.WARNING, [self._event("result", f"证据包已选入 {evidence_count} 条证据")], [self._section("pack", "对象身份", [("selected_evidence_count", str(evidence_count)), ("rerank_applied", "是")])]),
            },
            {
                f"{retrieval_id}:pack": self._observer_edge("边视角 · selected_into", "检索结果如何进入证据包。", status if evidence_count else RuntimeStatus.WARNING, [self._event("decision", "检索结果已被选入证据包")], [self._section("relation", "关系摘要", [("关系类型", "selected_into"), ("selected_count", str(evidence_count))])]),
            },
        )

    def _build_concept_candidate_review_stage(self, definition, context, status):
        entity_nodes = [
            self._node(f"{item['id']}:concept", item["name"], "concept_candidate", definition.stage_id, RuntimeStatus.COMPLETED, is_primary=index == 0, attributes={"category": item.get("category"), "alias_count": len(item.get("aliases", []))})
            for index, item in enumerate(context["entities"])
        ]
        nodes = entity_nodes or [self._node(f"{context['document_id']}:concept-empty", "概念候选为空", "concept_candidate", definition.stage_id, RuntimeStatus.WARNING, True, origin=RuntimeOrigin.UNAVAILABLE)]
        edges = [self._edge(f"{context['document_id']}:concept-pack:{node.node_id}", f"{context['document_id']}:evidence-pack-source", node.node_id, "proposes", definition.stage_id, RuntimeStatus.COMPLETED if entity_nodes else RuntimeStatus.WARNING) for node in entity_nodes]
        if entity_nodes:
            nodes.insert(0, self._node(f"{context['document_id']}:evidence-pack-source", "证据包输入", "evidence_pack_source", definition.stage_id, RuntimeStatus.COMPLETED, True, origin=RuntimeOrigin.DERIVED))
        return self._stage_snapshot(
            definition,
            status if entity_nodes else RuntimeStatus.WARNING,
            nodes,
            edges,
            self._observer_stage(
                title="阶段视角 · 概念审查",
                subtitle=context["document_title"],
                status=status if entity_nodes else RuntimeStatus.WARNING,
                stream=[self._event("progress", "证据包正在产出概念候选"), self._event("result", f"当前概念候选数：{len(context['entities'])}")],
                sections=[self._section("concepts", "概念候选摘要", [("entity_count", str(len(context["entities"]))), ("top_label", context["entities"][0]["name"] if context["entities"] else "无")])],
            ),
            {node.node_id: self._observer_node("节点视角 · 概念候选", "由证据包提出的概念候选对象。", node.status, [self._event("result", f"候选：{node.label}")], [self._section("candidate", "候选信息", [("label", node.label), ("category", str(node.attributes.get("category") or "未定"))])]) for node in entity_nodes},
            {},
        )

    def _build_relation_review_family_normalization_stage(self, definition, context, status):
        relation_nodes = [
            self._node(f"{context['document_id']}:relation:{index}", relation["type"], "relation_candidate", definition.stage_id, RuntimeStatus.COMPLETED, is_primary=index == 0, attributes={"source_name": relation.get("source_name"), "target_name": relation.get("target_name")})
            for index, relation in enumerate(context["relations"])
        ]
        nodes = relation_nodes or [self._node(f"{context['document_id']}:relation-empty", "关系候选为空", "relation_candidate", definition.stage_id, RuntimeStatus.WARNING, True, origin=RuntimeOrigin.UNAVAILABLE)]
        return self._stage_snapshot(
            definition,
            status if relation_nodes else RuntimeStatus.WARNING,
            nodes,
            [],
            self._observer_stage(
                title="阶段视角 · 关系/家族",
                subtitle=context["document_title"],
                status=status if relation_nodes else RuntimeStatus.WARNING,
                stream=[self._event("progress", "系统正在审查关系候选并做家族归一"), self._event("result", f"当前关系候选数：{len(context['relations'])}")],
                sections=[self._section("relations", "关系摘要", [("relation_count", str(len(context["relations"]))), ("has_aliases", "是" if any(item.get("aliases") for item in context["all_items"]) else "否")])],
            ),
            {node.node_id: self._observer_node("节点视角 · 关系候选", "关系审查阶段中的候选关系对象。", node.status, [self._event("result", f"关系类型：{node.label}")], [self._section("relation", "候选关系", [("source", str(node.attributes.get("source_name") or "未定")), ("target", str(node.attributes.get("target_name") or "未定"))])]) for node in relation_nodes},
            {},
        )

    def _build_definition_summary_conflict_consolidation_stage(self, definition, context, status):
        definition_id = f"{context['document_id']}:definition-summary"
        conflict_id = f"{context['document_id']}:conflict-summary"
        nodes = [
            self._node(definition_id, "定义汇总", "definition_candidate", definition.stage_id, RuntimeStatus.WARNING, True, origin=RuntimeOrigin.DERIVED, attributes={"source_item_count": len(context["all_items"])}),
            self._node(conflict_id, "冲突汇总", "conflict_candidate", definition.stage_id, RuntimeStatus.WARNING, origin=RuntimeOrigin.DERIVED, attributes={"relation_count": len(context["relations"])}),
        ]
        edges = [self._edge(f"{definition_id}:conflict", definition_id, conflict_id, "conflicts_with", definition.stage_id, RuntimeStatus.WARNING, True)]
        stage_status = RuntimeStatus.WARNING if context["all_items"] else RuntimeStatus.UNAVAILABLE
        return self._stage_snapshot(
            definition,
            stage_status,
            nodes,
            edges,
            self._observer_stage(
                title="阶段视角 · 定义/冲突",
                subtitle=context["document_title"],
                status=stage_status,
                stream=[self._event("warning", "当前系统尚未持久化独立的定义/冲突对象，本阶段为派生映射", level="warning"), self._event("result", f"依据 {len(context['all_items'])} 个知识对象和 {len(context['relations'])} 条关系生成摘要")],
                sections=[self._section("summary", "派生摘要", [("source_item_count", str(len(context["all_items"]))), ("relation_count", str(len(context["relations"])))])],
            ),
            {
                definition_id: self._observer_node("节点视角 · 定义汇总", "由当前知识对象派生的定义整合节点。", RuntimeStatus.WARNING, [self._event("warning", "当前为派生节点，后续应由真实阶段产物替代", level="warning")], [self._section("derived", "派生来源", [("source_item_count", str(len(context["all_items"])))])]),
            },
            {
                f"{definition_id}:conflict": self._observer_edge("边视角 · conflicts_with", "定义汇总与冲突汇总之间的关系。", RuntimeStatus.WARNING, [self._event("warning", "冲突关系为派生映射", level="warning")], [self._section("relation", "关系摘要", [("关系类型", "conflicts_with")])]),
            },
        )

    def _build_canonical_knowledge_stage(self, definition, context, status):
        nodes = [
            self._node(item["id"], item["name"], f"canonical_{item['kind']}", definition.stage_id, RuntimeStatus.COMPLETED, is_primary=index < 2, attributes={"kind": item["kind"], "category": item.get("category")})
            for index, item in enumerate(context["all_items"])
        ]
        edges: list[RuntimeGraphEdge] = []
        for index, relation in enumerate(context["relations"]):
            source = next((item["id"] for item in context["all_items"] if item["name"] == relation.get("source_name")), None)
            target = next((item["id"] for item in context["all_items"] if item["name"] == relation.get("target_name")), None)
            if source and target:
                edges.append(self._edge(f"{context['document_id']}:canonical:{index}", source, target, relation["type"], definition.stage_id, RuntimeStatus.COMPLETED, index < 2))
        stage_status = status if nodes else RuntimeStatus.UNAVAILABLE
        return self._stage_snapshot(
            definition,
            stage_status,
            nodes or [self._node(f"{context['document_id']}:canonical-empty", "规范对象为空", "canonical_item", definition.stage_id, RuntimeStatus.UNAVAILABLE, True, origin=RuntimeOrigin.UNAVAILABLE)],
            edges,
            self._observer_stage(
                title="阶段视角 · 规范知识",
                subtitle=context["document_title"],
                status=stage_status,
                stream=[self._event("progress", "概念、关系与定义候选正在汇聚为规范知识对象"), self._event("result", f"当前规范对象数：{len(context['all_items'])}")],
                sections=[self._section("canonical", "规范对象摘要", [("item_count", str(len(context["all_items"]))), ("relation_count", str(len(edges)))])],
            ),
            {node.node_id: self._observer_node("节点视角 · 规范对象", "当前文档在规范知识阶段形成的对象。", node.status, [self._event("result", f"规范对象：{node.label}")], [self._section("canonical", "对象摘要", [("kind", str(node.attributes.get("kind") or "unknown")), ("category", str(node.attributes.get("category") or "未定"))])]) for node in nodes},
            {edge.edge_id: self._observer_edge("边视角 · 规范关系", "规范知识阶段的对象关系。", edge.status, [self._event("result", f"关系类型：{edge.relation}")], [self._section("relation", "关系摘要", [("source", edge.source), ("target", edge.target), ("relation", edge.relation)])]) for edge in edges},
        )

    def _build_quality_policy_evaluation_governance_gate_stage(self, definition, context, status):
        evidence_count = len(context["evidence"])
        pending_reviews = [item for item in context["all_items"] if item.get("review_status", "pending") == "pending"]
        has_publication = bool(context["published_current_version"])
        rule_hit_id = f"{context['document_id']}:qg:rule-hit"
        gate_id = f"{context['document_id']}:qg:gate"
        blocked_id = f"{context['document_id']}:qg:blocked"
        publish_target_id = f"{context['document_id']}:qg:publish-target"
        nodes = [
            self._node(rule_hit_id, "规则命中", "rule_hit", definition.stage_id, RuntimeStatus.COMPLETED, True, origin=RuntimeOrigin.DERIVED, attributes={"rule_key": "min_supporting_documents", "evidence_count": evidence_count}),
            self._node(gate_id, "门禁决策", "gate_decision", definition.stage_id, RuntimeStatus.RUNNING if not has_publication else RuntimeStatus.COMPLETED, True, origin=RuntimeOrigin.DERIVED, attributes={"pending_review_count": len(pending_reviews)}),
        ]
        edges = [self._edge(f"{rule_hit_id}:gate", rule_hit_id, gate_id, "results_in", definition.stage_id, RuntimeStatus.RUNNING if not has_publication else RuntimeStatus.COMPLETED, True)]
        if not evidence_count:
            nodes.extend([
                self._node(blocked_id, "阻断结果", "blocked_result", definition.stage_id, RuntimeStatus.BLOCKED, origin=RuntimeOrigin.DERIVED, attributes={"reason": "证据不足"}),
            ])
            edges.extend([
                self._edge(f"{gate_id}:blocked", gate_id, blocked_id, "blocked_by", definition.stage_id, RuntimeStatus.BLOCKED, True),
            ])
            gate_status = RuntimeStatus.BLOCKED
        else:
            publish_status = RuntimeStatus.COMPLETED if has_publication else RuntimeStatus.WARNING if pending_reviews else RuntimeStatus.RUNNING
            nodes.append(self._node(publish_target_id, "发布目标", "publish_target", definition.stage_id, publish_status, origin=RuntimeOrigin.DERIVED, attributes={"version_label": (context["published_current_version"] or {}).get("version_label"), "pending_review_count": len(pending_reviews)}))
            edges.append(self._edge(f"{gate_id}:publish", gate_id, publish_target_id, "publishes_to", definition.stage_id, publish_status, True, attributes={"policy_note": "pending_review_after_publish" if pending_reviews else "ready"}))
            gate_status = publish_status
        return self._stage_snapshot(
            definition,
            gate_status,
            nodes,
            edges,
            self._observer_stage(
                title="阶段视角 · 质量门禁",
                subtitle=context["document_title"],
                status=gate_status,
                stream=[self._event("rule", f"命中规则：min_supporting_documents，当前证据数 {evidence_count}", level="warning" if evidence_count <= 1 else "success"), self._event("block" if gate_status == RuntimeStatus.BLOCKED else "result", "当前对象因证据不足被规则阻断" if gate_status == RuntimeStatus.BLOCKED else "当前对象按规则进入发布目标，正式入库前再进入人工审核", level="danger" if gate_status == RuntimeStatus.BLOCKED else "success")],
                sections=[self._section("gate", "门禁摘要", [("evidence_count", str(evidence_count)), ("pending_review_count", str(len(pending_reviews))), ("current_version", (context["published_current_version"] or {}).get("version_label") or "未发布")])],
            ),
            {
                rule_hit_id: self._observer_node("节点视角 · 规则命中", "质量门禁阶段的规则命中对象。", RuntimeStatus.COMPLETED, [self._event("rule", "最少支撑文档规则已完成评估")], [self._section("rule", "规则信息", [("rule_key", "min_supporting_documents"), ("evidence_count", str(evidence_count))])]),
                gate_id: self._observer_node("节点视角 · 门禁决策", "门禁阶段的核心决策节点。", gate_status, [self._event("decision", "门禁决策正在汇总规则、告警与复核结果")], [self._section("decision", "决策摘要", [("gate_status", gate_status.value), ("pending_review_count", str(len(pending_reviews)))])]),
            },
            {
                f"{rule_hit_id}:gate": self._observer_edge("边视角 · results_in", "规则命中如何形成门禁决策。", gate_status, [self._event("result", "规则命中结果流入门禁决策")], [self._section("relation", "关系摘要", [("关系类型", "results_in"), ("源对象", "规则命中"), ("目标对象", "门禁决策")])]),
            },
        )

    def _build_indexes_snapshots_apis_stage(self, definition, context, status):
        document_published = bool(context["published_current_version"])
        return build_indexes_snapshots_apis_snapshot(
            archive_id=context["archive_id"],
            document_id=context["document_id"],
            document_title=context["document_title"],
            current_version=context["published_current_version"],
            document_published=document_published,
            knowledge_items=context["all_items"],
            status_override=status if status == RuntimeStatus.RUNNING else None,
        )
