from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.archive_knowledge.document_artifacts import DocumentArtifactRepository
from app.archive_knowledge.policy_config import DEFAULT_STAGE_ORDER, normalize_archive_policy_config
from app.archive_knowledge.repository import JsonPublishedKnowledgeRepository
from app.archive_knowledge.runtime_repository import DocumentRuntimeRepository


class PolicyRuleChange(BaseModel):
    stage_id: str
    rule_id: str
    change_type: str
    previous_rule_hash: str | None = None
    next_rule_hash: str | None = None
    previous_rule_version: str | None = None
    next_rule_version: str | None = None


class ImpactSet(BaseModel):
    impact_id: str
    archive_id: str
    changed_rule_ids: list[str] = Field(default_factory=list)
    changed_stage_ids: list[str] = Field(default_factory=list)
    affected_docs: list[str] = Field(default_factory=list)
    affected_document_ids: list[str] = Field(default_factory=list)
    affected_stages: list[str] = Field(default_factory=list)
    affected_stage_ids: list[str] = Field(default_factory=list)
    affected_chunks: list[str] = Field(default_factory=list)
    affected_chunk_ids: list[str] = Field(default_factory=list)
    affected_candidates: list[str] = Field(default_factory=list)
    affected_candidate_ids: list[str] = Field(default_factory=list)
    affected_relations: list[str] = Field(default_factory=list)
    affected_relation_ids: list[str] = Field(default_factory=list)
    affected_publication_snapshots: list[str] = Field(default_factory=list)
    affected_publication_snapshot_ids: list[str] = Field(default_factory=list)
    minimum_rebuild_stage_id: str | None = None
    source_policy_snapshot_id: str | None = None
    target_policy_snapshot_id: str | None = None
    rule_changes: list[PolicyRuleChange] = Field(default_factory=list)
    generated_at: str


class IncrementalRebuildTask(BaseModel):
    task_id: str
    archive_id: str
    status: str = "queued"
    mode: str = "incremental_recompute_candidate_only"
    minimum_rebuild_stage_id: str | None = None
    start_stage_id: str | None = None
    affected_document_ids: list[str] = Field(default_factory=list)
    affected_stage_ids: list[str] = Field(default_factory=list)
    impact_set: ImpactSet
    writes_official_knowledge: bool = False
    output_policy: str = "candidate_or_pending_confirmation_only"
    allowed_outputs: list[str] = Field(
        default_factory=lambda: [
            "new_runtime_candidates",
            "pending_governance_confirmation_results",
        ]
    )
    created_at: str
    candidate_artifact_path: str | None = None


class ArchiveRuntimeIncrementalRebuildService:
    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)
        self.artifact_repository = DocumentArtifactRepository(self.output_root)
        self.runtime_repository = DocumentRuntimeRepository(self.output_root)
        self.published_repository = JsonPublishedKnowledgeRepository(self.output_root)

    def plan_policy_change(
        self,
        archive_id: str,
        previous_config: dict[str, Any] | None,
        next_config: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        impact_set = self.compute_impact_set(
            archive_id,
            previous_config=previous_config,
            next_config=next_config,
        )
        if not impact_set.changed_rule_ids and not impact_set.changed_stage_ids:
            return None

        task = self.create_incremental_rebuild_task(archive_id, impact_set)
        return {
            "impact_set": impact_set.model_dump(mode="json"),
            "incremental_rebuild_task": task.model_dump(mode="json"),
        }

    def compute_impact_set(
        self,
        archive_id: str,
        *,
        previous_config: dict[str, Any] | None,
        next_config: dict[str, Any] | None,
    ) -> ImpactSet:
        generated_at = datetime.now(UTC).isoformat()
        previous = normalize_archive_policy_config(archive_id, previous_config)
        next_policy = normalize_archive_policy_config(archive_id, next_config)
        rule_changes = self._diff_rule_changes(previous, next_policy)
        changed_stage_ids = self._changed_stage_ids(previous, next_policy, rule_changes)
        minimum_rebuild_stage_id = self._minimum_stage_id(changed_stage_ids)
        affected_stage_ids = self._downstream_stage_ids(minimum_rebuild_stage_id)

        affected = self._collect_affected_runtime_objects(
            archive_id=archive_id,
            affected_stage_ids=affected_stage_ids,
            changed_stage_ids=changed_stage_ids,
            changed_rule_ids=[change.rule_id for change in rule_changes],
        )
        impact_payload = {
            "archive_id": archive_id,
            "changed_rule_ids": [change.rule_id for change in rule_changes],
            "changed_stage_ids": changed_stage_ids,
            "affected_document_ids": affected["documents"],
            "affected_stage_ids": affected_stage_ids,
            "affected_chunk_ids": affected["chunks"],
            "affected_candidate_ids": affected["candidates"],
            "affected_relation_ids": affected["relations"],
            "affected_publication_snapshot_ids": affected["publication_snapshots"],
            "minimum_rebuild_stage_id": minimum_rebuild_stage_id,
            "source_policy_snapshot_id": self._policy_snapshot_ref(previous),
            "target_policy_snapshot_id": self._policy_snapshot_ref(next_policy),
            "rule_changes": [change.model_dump(mode="json") for change in rule_changes],
            "generated_at": generated_at,
        }
        impact_id = "impact-" + self._short_hash(impact_payload)
        return ImpactSet(
            impact_id=impact_id,
            archive_id=archive_id,
            changed_rule_ids=impact_payload["changed_rule_ids"],
            changed_stage_ids=changed_stage_ids,
            affected_docs=affected["documents"],
            affected_document_ids=affected["documents"],
            affected_stages=affected_stage_ids,
            affected_stage_ids=affected_stage_ids,
            affected_chunks=affected["chunks"],
            affected_chunk_ids=affected["chunks"],
            affected_candidates=affected["candidates"],
            affected_candidate_ids=affected["candidates"],
            affected_relations=affected["relations"],
            affected_relation_ids=affected["relations"],
            affected_publication_snapshots=affected["publication_snapshots"],
            affected_publication_snapshot_ids=affected["publication_snapshots"],
            minimum_rebuild_stage_id=minimum_rebuild_stage_id,
            source_policy_snapshot_id=impact_payload["source_policy_snapshot_id"],
            target_policy_snapshot_id=impact_payload["target_policy_snapshot_id"],
            rule_changes=rule_changes,
            generated_at=generated_at,
        )

    def create_incremental_rebuild_task(
        self,
        archive_id: str,
        impact_set: ImpactSet,
    ) -> IncrementalRebuildTask:
        created_at = datetime.now(UTC).isoformat()
        task_payload = {
            "archive_id": archive_id,
            "impact_id": impact_set.impact_id,
            "minimum_rebuild_stage_id": impact_set.minimum_rebuild_stage_id,
            "affected_document_ids": impact_set.affected_document_ids,
            "created_at": created_at,
        }
        task_id = "irt-" + self._short_hash(task_payload)
        task_dir = self._task_dir(archive_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        candidate_artifact_path = task_dir / f"{task_id}-candidates.json"
        task = IncrementalRebuildTask(
            task_id=task_id,
            archive_id=archive_id,
            minimum_rebuild_stage_id=impact_set.minimum_rebuild_stage_id,
            start_stage_id=impact_set.minimum_rebuild_stage_id,
            affected_document_ids=impact_set.affected_document_ids,
            affected_stage_ids=impact_set.affected_stage_ids,
            impact_set=impact_set,
            created_at=created_at,
            candidate_artifact_path=str(candidate_artifact_path),
        )
        task_path = task_dir / f"{task_id}.json"
        task_path.write_text(
            json.dumps(task.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        candidate_artifact_path.write_text(
            json.dumps(
                {
                    "task_id": task_id,
                    "archive_id": archive_id,
                    "status": "pending_recompute",
                    "output_policy": task.output_policy,
                    "minimum_rebuild_stage_id": impact_set.minimum_rebuild_stage_id,
                    "affected_document_ids": impact_set.affected_document_ids,
                    "candidate_results": [],
                    "writes_official_knowledge": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return task

    def load_incremental_rebuild_task(self, archive_id: str, task_id: str) -> dict[str, Any] | None:
        path = self._task_dir(archive_id) / f"{task_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_incremental_rebuild_tasks(self, archive_id: str) -> list[dict[str, Any]]:
        task_dir = self._task_dir(archive_id)
        if not task_dir.exists():
            return []
        tasks = []
        for path in sorted(task_dir.glob("irt-*.json")):
            if path.name.endswith("-candidates.json"):
                continue
            tasks.append(json.loads(path.read_text(encoding="utf-8")))
        return tasks

    def _diff_rule_changes(
        self,
        previous: dict[str, Any],
        next_policy: dict[str, Any],
    ) -> list[PolicyRuleChange]:
        previous_rules = self._rules_by_identity(previous)
        next_rules = self._rules_by_identity(next_policy)
        changes: list[PolicyRuleChange] = []
        for identity in sorted(previous_rules.keys() | next_rules.keys(), key=lambda item: (self._stage_order(item[0]), item[1])):
            stage_id, rule_id = identity
            previous_rule = previous_rules.get(identity)
            next_rule = next_rules.get(identity)
            if previous_rule is None and next_rule is not None:
                changes.append(
                    PolicyRuleChange(
                        stage_id=stage_id,
                        rule_id=rule_id,
                        change_type="added",
                        next_rule_hash=next_rule.get("rule_hash"),
                        next_rule_version=next_rule.get("rule_version"),
                    )
                )
                continue
            if previous_rule is not None and next_rule is None:
                changes.append(
                    PolicyRuleChange(
                        stage_id=stage_id,
                        rule_id=rule_id,
                        change_type="removed",
                        previous_rule_hash=previous_rule.get("rule_hash"),
                        previous_rule_version=previous_rule.get("rule_version"),
                    )
                )
                continue
            if previous_rule is None or next_rule is None:
                continue
            if self._rule_change_fingerprint(previous_rule) == self._rule_change_fingerprint(next_rule):
                continue
            changes.append(
                PolicyRuleChange(
                    stage_id=stage_id,
                    rule_id=rule_id,
                    change_type="modified",
                    previous_rule_hash=previous_rule.get("rule_hash"),
                    next_rule_hash=next_rule.get("rule_hash"),
                    previous_rule_version=previous_rule.get("rule_version"),
                    next_rule_version=next_rule.get("rule_version"),
                )
            )
        return changes

    def _changed_stage_ids(
        self,
        previous: dict[str, Any],
        next_policy: dict[str, Any],
        rule_changes: list[PolicyRuleChange],
    ) -> list[str]:
        changed_stage_ids = {change.stage_id for change in rule_changes}
        previous_stages = previous.get("stages", {})
        next_stages = next_policy.get("stages", {})
        for stage_id in DEFAULT_STAGE_ORDER:
            previous_stage = previous_stages.get(stage_id) if isinstance(previous_stages, dict) else None
            next_stage = next_stages.get(stage_id) if isinstance(next_stages, dict) else None
            if not isinstance(previous_stage, dict) or not isinstance(next_stage, dict):
                if previous_stage != next_stage:
                    changed_stage_ids.add(stage_id)
                continue
            if self._stage_change_fingerprint(previous_stage) != self._stage_change_fingerprint(next_stage):
                changed_stage_ids.add(stage_id)
        return sorted(changed_stage_ids, key=self._stage_order)

    def _collect_affected_runtime_objects(
        self,
        *,
        archive_id: str,
        affected_stage_ids: list[str],
        changed_stage_ids: list[str],
        changed_rule_ids: list[str],
    ) -> dict[str, list[str]]:
        documents: list[str] = []
        chunks: list[str] = []
        candidates: list[str] = []
        relations: list[str] = []
        publication_snapshots: list[str] = []
        affected_stage_set = set(affected_stage_ids)
        changed_stage_set = set(changed_stage_ids)
        changed_rule_set = set(changed_rule_ids)

        for document in self.artifact_repository.list_documents(archive_id):
            if not document.get("included_in_archive", True):
                continue
            document_id = str(document.get("document_id") or "")
            if not document_id:
                continue
            contribution = self._load_contribution(archive_id, document_id)
            document_touched = bool(affected_stage_set)

            if contribution is not None:
                for collection_name in ("entities", "events", "processes"):
                    for item in contribution.get(collection_name, []):
                        self._append_unique(candidates, item.get("id"))
                for index, relation in enumerate(contribution.get("relations", []), start=1):
                    relation_id = relation.get("id") or f"{document_id}:relation:{index}"
                    self._append_unique(relations, relation_id)

            for stage_id in self.runtime_repository.list_stage_snapshot_ids(archive_id, document_id):
                if stage_id not in affected_stage_set:
                    continue
                snapshot = self.runtime_repository.load_stage_snapshot(archive_id, document_id, stage_id) or {}
                document_touched = True
                self._collect_snapshot_objects(
                    snapshot=snapshot,
                    chunks=chunks,
                    candidates=candidates,
                    relations=relations,
                    publication_snapshots=publication_snapshots,
                )
                self._collect_rule_record_objects(
                    snapshot=snapshot,
                    changed_stage_set=changed_stage_set,
                    changed_rule_set=changed_rule_set,
                    chunks=chunks,
                    candidates=candidates,
                    relations=relations,
                    publication_snapshots=publication_snapshots,
                )

            if document_touched:
                self._append_unique(documents, document_id)

        self._collect_publication_files(archive_id, publication_snapshots)
        return {
            "documents": documents,
            "chunks": chunks,
            "candidates": candidates,
            "relations": relations,
            "publication_snapshots": publication_snapshots,
        }

    def _collect_snapshot_objects(
        self,
        *,
        snapshot: dict[str, Any],
        chunks: list[str],
        candidates: list[str],
        relations: list[str],
        publication_snapshots: list[str],
    ) -> None:
        graph = snapshot.get("graph") if isinstance(snapshot.get("graph"), dict) else {}
        for node in graph.get("nodes", []):
            if not isinstance(node, dict):
                continue
            node_id = node.get("node_id")
            node_type = str(node.get("node_type") or "").lower()
            if "chunk" in node_type or ":chunk" in str(node_id):
                self._append_unique(chunks, node_id)
            if "candidate" in node_type or "canonical" in node_type:
                self._append_unique(candidates, node_id)
            if "relation" in node_type:
                self._append_unique(relations, node_id)
            if "publication" in node_type or "snapshot" in node_type:
                self._append_unique(publication_snapshots, node_id)
        for edge in graph.get("edges", []):
            if isinstance(edge, dict):
                self._append_unique(relations, edge.get("edge_id"))

    def _collect_rule_record_objects(
        self,
        *,
        snapshot: dict[str, Any],
        changed_stage_set: set[str],
        changed_rule_set: set[str],
        chunks: list[str],
        candidates: list[str],
        relations: list[str],
        publication_snapshots: list[str],
    ) -> None:
        for record in snapshot.get("rule_execution_records", []):
            if not isinstance(record, dict):
                continue
            stage_id = str(record.get("stage_id") or snapshot.get("stage_id") or "")
            rule_id = str(record.get("rule_id") or "")
            record_is_relevant = stage_id in changed_stage_set or not changed_rule_set or rule_id in changed_rule_set
            if not record_is_relevant:
                continue
            for object_id in self._as_string_list(record.get("affected_object_ids")):
                self._append_impacted_object(object_id, chunks, candidates, relations, publication_snapshots)
            for relation_id in self._as_string_list(record.get("affected_relation_ids")):
                self._append_unique(relations, relation_id)
            for ref in [
                *self._as_string_list(record.get("input_artifact_refs")),
                *self._as_string_list(record.get("output_artifact_refs")),
            ]:
                self._append_impacted_object(ref, chunks, candidates, relations, publication_snapshots)

    def _collect_publication_files(self, archive_id: str, publication_snapshots: list[str]) -> None:
        for path in sorted(self.output_root.glob(f"{archive_id}-published-*.json")):
            self._append_unique(publication_snapshots, path.name)
        try:
            _payload, current_version = self.published_repository.load_latest(archive_id)
        except Exception:
            current_version = None
        if current_version and current_version.get("version_label"):
            self._append_unique(publication_snapshots, str(current_version["version_label"]))

    def _append_impacted_object(
        self,
        object_id: str,
        chunks: list[str],
        candidates: list[str],
        relations: list[str],
        publication_snapshots: list[str],
    ) -> None:
        lowered = object_id.lower()
        if "chunk" in lowered:
            self._append_unique(chunks, object_id)
        elif "relation" in lowered or ":edge" in lowered:
            self._append_unique(relations, object_id)
        elif "publication" in lowered or "snapshot" in lowered or "publish" in lowered:
            self._append_unique(publication_snapshots, object_id)
        else:
            self._append_unique(candidates, object_id)

    def _load_contribution(self, archive_id: str, document_id: str) -> dict[str, Any] | None:
        try:
            return self.artifact_repository.load_document_contribution(archive_id, document_id)
        except FileNotFoundError:
            return None

    def _downstream_stage_ids(self, minimum_rebuild_stage_id: str | None) -> list[str]:
        if minimum_rebuild_stage_id is None:
            return []
        minimum_order = self._stage_order(minimum_rebuild_stage_id)
        return [stage_id for stage_id in DEFAULT_STAGE_ORDER if self._stage_order(stage_id) >= minimum_order]

    def _minimum_stage_id(self, stage_ids: list[str]) -> str | None:
        if not stage_ids:
            return None
        return min(stage_ids, key=self._stage_order)

    @staticmethod
    def _rules_by_identity(config: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
        result: dict[tuple[str, str], dict[str, Any]] = {}
        stages = config.get("stages", {})
        if not isinstance(stages, dict):
            return result
        for stage_id, stage in stages.items():
            if not isinstance(stage, dict):
                continue
            for rule in stage.get("rules", []):
                if not isinstance(rule, dict):
                    continue
                rule_id = str(rule.get("rule_id") or rule.get("key") or "").strip()
                if rule_id:
                    result[(str(stage_id), rule_id)] = rule
        return result

    @staticmethod
    def _rule_change_fingerprint(rule: dict[str, Any]) -> dict[str, Any]:
        return {
            "rule_hash": rule.get("rule_hash"),
            "rule_version": rule.get("rule_version"),
            "threshold": rule.get("threshold"),
            "action": rule.get("action"),
            "effect_kind": rule.get("effect_kind"),
            "scope_selector": rule.get("scope_selector"),
            "input_schema": rule.get("input_schema"),
            "output_schema": rule.get("output_schema"),
            "parameters": rule.get("parameters"),
            "trace_fields": rule.get("trace_fields"),
        }

    @staticmethod
    def _stage_change_fingerprint(stage: dict[str, Any]) -> dict[str, Any]:
        return {
            "enabled": stage.get("enabled"),
            "default_action": stage.get("default_action"),
            "inputs": stage.get("inputs"),
            "outputs": stage.get("outputs"),
            "observability": stage.get("observability"),
            "rules": [
                ArchiveRuntimeIncrementalRebuildService._rule_change_fingerprint(rule)
                for rule in stage.get("rules", [])
                if isinstance(rule, dict)
            ],
        }

    @staticmethod
    def _policy_snapshot_ref(config: dict[str, Any]) -> str | None:
        return (
            config.get("policy_snapshot_id")
            or config.get("snapshot_id")
            or config.get("policy_package_version_id")
            or config.get("policy_package_version_hash")
        )

    @staticmethod
    def _stage_order(stage_id: str) -> int:
        try:
            return DEFAULT_STAGE_ORDER.index(stage_id)
        except ValueError:
            return len(DEFAULT_STAGE_ORDER) + 100

    @staticmethod
    def _as_string_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if item is not None and str(item)]
        if value is None or value == "":
            return []
        return [str(value)]

    @staticmethod
    def _append_unique(values: list[str], value: Any) -> None:
        if value is None:
            return
        normalized = str(value)
        if not normalized or normalized in values:
            return
        values.append(normalized)

    @staticmethod
    def _short_hash(payload: Any) -> str:
        normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return sha256(normalized.encode("utf-8")).hexdigest()[:12]

    def _task_dir(self, archive_id: str) -> Path:
        return self.output_root / f"{archive_id}-incremental-rebuild-tasks"
