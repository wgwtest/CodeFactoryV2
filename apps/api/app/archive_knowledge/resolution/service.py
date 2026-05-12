from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
from typing import Any, Literal

from app.archive_knowledge.contracts import (
    ArchiveKnowledgeResolutionSnapshot,
    ArtifactRef,
    CanonicalKnowledgeItem,
    CrossDocumentMatchCandidate,
    ImpactSet,
    KnowledgeIdentityKey,
    KnowledgeMergeDecision,
    KnowledgeResolutionTrace,
    KnowledgeUpdatePlan,
    P1ResponseEnvelope,
    ResolvedKnowledgeObject,
    ResolvedKnowledgeRelation,
)
from app.archive_knowledge.document_artifacts import DocumentArtifactRepository
from app.archive_knowledge.identity import normalize_identity_text, short_identity_hash


ITEM_COLLECTIONS: tuple[tuple[str, str], ...] = (
    ("entities", "entity"),
    ("events", "event"),
    ("processes", "process"),
    ("capabilities", "capability"),
    ("systems", "system"),
    ("nodes", "node"),
    ("information_exchanges", "information_exchange"),
)

VIEW_TOKEN_RE = re.compile(
    r"\b(?:av|cv|ov|sv|stdv|svc? v|tv)\s*[- ]?\s*\d+[a-z]?\b"
    r"|\b(?:operational|systems?|service|all|standards?)\s+view\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DocumentKnowledgeCandidate:
    archive_id: str
    document_id: str
    document_title: str
    source_archive: str
    candidate_item_id: str
    local_item_id: str
    object_type: str
    category: str
    display_name: str
    aliases: tuple[str, ...]
    definition: str | None
    has_explicit_definition: bool
    relation_terms: tuple[str, ...]
    relation_refs: tuple[str, ...]
    evidence_refs: tuple[ArtifactRef, ...]
    source_rule_execution_ids: tuple[str, ...]
    conflict_reasons: tuple[str, ...]


@dataclass(frozen=True)
class DocumentRelationCandidate:
    archive_id: str
    document_id: str
    relation_candidate_id: str
    relation_type: str
    source_name: str
    target_name: str
    evidence_refs: tuple[ArtifactRef, ...]
    confidence: float | None
    source_rule_execution_ids: tuple[str, ...]


class ArchiveKnowledgeResolutionService:
    """Build candidate-only same-knowledge resolution snapshots from document artifacts."""

    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)
        self.artifact_repository = DocumentArtifactRepository(self.output_root)

    def build_latest_resolution_envelope(
        self,
        archive_id: str,
        *,
        runtime_snapshot_id: str | None = None,
        policy_package_version_id: str | None = None,
    ) -> P1ResponseEnvelope[ArchiveKnowledgeResolutionSnapshot] | None:
        snapshot = self.build_latest_resolution_snapshot(
            archive_id,
            runtime_snapshot_id=runtime_snapshot_id,
            policy_package_version_id=policy_package_version_id,
        )
        if snapshot is None:
            return None
        return P1ResponseEnvelope(
            contract_version="p1.knowledge_resolution.r1",
            source_kind="live",
            generated_at=snapshot.generated_at,
            data=snapshot,
            warnings=[],
        )

    def build_latest_resolution_snapshot(
        self,
        archive_id: str,
        *,
        runtime_snapshot_id: str | None = None,
        policy_package_version_id: str | None = None,
    ) -> ArchiveKnowledgeResolutionSnapshot | None:
        if not self.artifact_repository.has_manifest(archive_id):
            return None

        generated_at = datetime.now(UTC).isoformat()
        contributions = self.artifact_repository.load_contributions(archive_id, included_only=True)
        candidates = self._collect_candidates(archive_id, contributions)
        candidate_relations = self._collect_relations(archive_id, contributions)
        match_candidates = self._build_match_candidates(candidates, generated_at=generated_at)
        merge_decisions = self._build_merge_decisions(match_candidates, candidates, generated_at=generated_at)
        canonical_items, candidate_to_object_id, grouped_candidates = self._build_canonical_items(candidates, match_candidates)
        update_plan = self._build_update_plan(archive_id, canonical_items, generated_at=generated_at)
        resolved_objects = self._build_resolved_objects(
            grouped_candidates,
            match_candidates,
            update_plan=update_plan,
        )
        resolved_relations, relation_trace = self._build_resolved_relations(
            candidate_relations,
            candidates,
            resolved_objects,
            candidate_to_object_id,
        )
        resolution_trace = self._build_resolution_trace(
            resolved_objects,
            resolved_relations,
            match_candidates,
            merge_decisions,
            relation_trace,
            update_plan=update_plan,
        )

        conflict_count = sum(1 for candidate in match_candidates if candidate.suggested_action == "mark_conflict")
        unsupported_count = sum(1 for candidate in match_candidates if candidate.suggested_action == "keep_separate")
        payload = {
            "archive_id": archive_id,
            "runtime_snapshot_id": runtime_snapshot_id,
            "policy_package_version_id": policy_package_version_id,
            "candidate_ids": [candidate.candidate_item_id for candidate in candidates],
            "match_ids": [candidate.candidate_id for candidate in match_candidates],
            "canonical_ids": [item.knowledge_id for item in canonical_items],
            "relation_ids": [relation.relation_id for relation in resolved_relations],
            "update_plan_id": update_plan.update_plan_id if update_plan else None,
        }
        return ArchiveKnowledgeResolutionSnapshot(
            snapshot_id=f"RESOLVE-{short_identity_hash(payload)}",
            archive_id=archive_id,
            run_id=runtime_snapshot_id,
            policy_snapshot_id=self._policy_snapshot_id(contributions),
            runtime_snapshot_id=runtime_snapshot_id,
            policy_package_version_id=policy_package_version_id or self._policy_package_version_id(contributions),
            input_document_ids=self._input_document_ids(contributions),
            generated_at=generated_at,
            match_candidates=match_candidates,
            merge_decisions=merge_decisions,
            canonical_items=canonical_items,
            resolved_objects=resolved_objects,
            resolved_relations=resolved_relations,
            resolution_trace=resolution_trace,
            update_plan=update_plan,
            conflict_count=max(
                conflict_count,
                sum(1 for item in resolved_objects if item.conflict_status in {"conflict_pending", "rule_conflict"}),
            ),
            unsupported_count=unsupported_count,
        )

    def build_latest_impact_envelope(self, archive_id: str) -> P1ResponseEnvelope[ImpactSet] | None:
        latest_task = self._load_latest_incremental_task(archive_id)
        if latest_task is None:
            return None
        impact_set = self._contract_impact_set(archive_id, latest_task)
        return P1ResponseEnvelope(
            contract_version="p1.impact_set.r1",
            source_kind="live",
            generated_at=impact_set.generated_at or datetime.now(UTC).isoformat(),
            data=impact_set,
            warnings=[],
        )

    def _collect_candidates(
        self,
        archive_id: str,
        contributions: list[dict[str, Any]],
    ) -> list[DocumentKnowledgeCandidate]:
        candidates: list[DocumentKnowledgeCandidate] = []
        for contribution in sorted(contributions, key=lambda item: str(item.get("document", {}).get("path") or "")):
            document = contribution.get("document") or {}
            document_id = str(document.get("id") or "")
            if not document_id:
                continue
            document_title = str(document.get("title") or document_id)
            source_archive = str(document.get("source_archive") or archive_id)
            rule_execution_ids = self._collect_rule_execution_ids(contribution)

            for collection_name, object_type in ITEM_COLLECTIONS:
                for index, item in enumerate(contribution.get(collection_name, []), start=1):
                    if not isinstance(item, dict):
                        continue
                    display_name = str(item.get("name") or item.get("display_name") or "").strip()
                    if not display_name:
                        continue
                    local_item_id = str(item.get("id") or f"{object_type}-{short_identity_hash([document_id, display_name, index])}")
                    candidate_item_id = f"{document_id}:{local_item_id}"
                    evidence_refs = tuple(self._build_evidence_refs(document_id, local_item_id, item.get("evidence", [])))
                    relation_terms, relation_refs = self._relation_neighborhood(contribution, item, document_id)
                    definition = self._definition_text(item, evidence_refs)
                    has_explicit_definition = bool(item.get("definition") or item.get("description") or item.get("summary"))
                    aliases = tuple(self._as_unique_strings(item.get("aliases", [])))
                    resolved_object_type = self._knowledge_object_type(object_type, item)
                    candidates.append(
                        DocumentKnowledgeCandidate(
                            archive_id=archive_id,
                            document_id=document_id,
                            document_title=document_title,
                            source_archive=source_archive,
                            candidate_item_id=candidate_item_id,
                            local_item_id=local_item_id,
                            object_type=resolved_object_type,
                            category=str(item.get("category") or object_type),
                            display_name=display_name,
                            aliases=aliases,
                            definition=definition,
                            has_explicit_definition=has_explicit_definition,
                            relation_terms=tuple(relation_terms),
                            relation_refs=tuple(relation_refs),
                            evidence_refs=evidence_refs,
                            source_rule_execution_ids=tuple(rule_execution_ids),
                            conflict_reasons=tuple(self._collect_item_conflict_reasons(item)),
                        )
                    )
        return candidates

    def _collect_relations(
        self,
        archive_id: str,
        contributions: list[dict[str, Any]],
    ) -> list[DocumentRelationCandidate]:
        relations: list[DocumentRelationCandidate] = []
        for contribution in sorted(contributions, key=lambda item: str(item.get("document", {}).get("path") or "")):
            document = contribution.get("document") or {}
            document_id = str(document.get("id") or "")
            if not document_id:
                continue
            rule_execution_ids = tuple(self._collect_rule_execution_ids(contribution))
            for index, relation in enumerate(contribution.get("relations", []), start=1):
                if not isinstance(relation, dict):
                    continue
                source_name = str(relation.get("source_name") or relation.get("source") or relation.get("from") or "").strip()
                target_name = str(relation.get("target_name") or relation.get("target") or relation.get("to") or "").strip()
                if not source_name or not target_name:
                    continue
                raw_relation_id = str(relation.get("id") or f"relation:{index}")
                local_relation_id = raw_relation_id if raw_relation_id.startswith(document_id) else f"{document_id}:{raw_relation_id}"
                evidence_value = relation.get("evidence_refs") or relation.get("evidence_anchors") or relation.get("evidence")
                evidence_refs = tuple(self._build_evidence_refs(document_id, local_relation_id, evidence_value))
                relations.append(
                    DocumentRelationCandidate(
                        archive_id=archive_id,
                        document_id=document_id,
                        relation_candidate_id=local_relation_id,
                        relation_type=self._normalize_relation_type(
                            relation.get("type") or relation.get("relation_type") or "related_to"
                        ),
                        source_name=source_name,
                        target_name=target_name,
                        evidence_refs=evidence_refs,
                        confidence=self._optional_float(relation.get("confidence")),
                        source_rule_execution_ids=rule_execution_ids,
                    )
                )
        return relations

    def _build_match_candidates(
        self,
        candidates: list[DocumentKnowledgeCandidate],
        *,
        generated_at: str,
    ) -> list[CrossDocumentMatchCandidate]:
        matches: list[CrossDocumentMatchCandidate] = []
        for left_index, left in enumerate(candidates):
            for right in candidates[left_index + 1 :]:
                if left.document_id == right.document_id:
                    continue
                features = self._match_features(left, right)
                score = round(
                    features["name_score"] * 0.4
                    + features["definition_score"] * 0.22
                    + features["relation_score"] * 0.18
                    + features["evidence_overlap_score"] * 0.08
                    + features["view_number_score"] * 0.12,
                    3,
                )
                action = self._suggest_action(left, right, features, score)
                if action is None:
                    continue
                source_candidate_ids = sorted([left.candidate_item_id, right.candidate_item_id])
                match_id = f"MATCH-{short_identity_hash([left.archive_id, *source_candidate_ids, score])}"
                matches.append(
                    CrossDocumentMatchCandidate(
                        candidate_id=match_id,
                        identity_key=self._identity_key(left, right),
                        source_candidate_item_ids=source_candidate_ids,
                        source_document_ids=sorted([left.document_id, right.document_id]),
                        similarity_score=score,
                        match_features=features,
                        evidence_refs=self._unique_artifact_refs([*left.evidence_refs, *right.evidence_refs]),
                        suggested_action=action,
                        explanation=self._match_explanation(action, features),
                        generated_at=generated_at,
                    )
                )
        return sorted(matches, key=lambda item: (-item.similarity_score, item.candidate_id))

    def _build_merge_decisions(
        self,
        match_candidates: list[CrossDocumentMatchCandidate],
        candidates: list[DocumentKnowledgeCandidate],
        *,
        generated_at: str,
    ) -> list[KnowledgeMergeDecision]:
        candidates_by_id = {candidate.candidate_item_id: candidate for candidate in candidates}
        decisions = []
        for match_candidate in match_candidates:
            source_candidate_ids = list(match_candidate.source_candidate_item_ids)
            source_candidates = [candidates_by_id[item_id] for item_id in source_candidate_ids if item_id in candidates_by_id]
            rule_execution_record_ids = self._unique_strings(
                rule_id
                for source_candidate in source_candidates
                for rule_id in source_candidate.source_rule_execution_ids
            )
            if not rule_execution_record_ids:
                rule_execution_record_ids = [f"derived-resolution-{short_identity_hash(source_candidate_ids)}"]
            decision = self._decision_for_action(match_candidate.suggested_action)
            decisions.append(
                KnowledgeMergeDecision(
                    decision_id=f"MERGE-{short_identity_hash([match_candidate.candidate_id, decision])}",
                    candidate_ids=[match_candidate.candidate_id],
                    source_candidate_item_ids=source_candidate_ids,
                    decision=decision,
                    reason=self._decision_reason(match_candidate),
                    rule_execution_record_ids=rule_execution_record_ids,
                    requires_governance_confirmation=decision in {"conflict_pending", "replaced"},
                    generated_at=generated_at,
                )
            )
        return decisions

    def _build_canonical_items(
        self,
        candidates: list[DocumentKnowledgeCandidate],
        match_candidates: list[CrossDocumentMatchCandidate],
    ) -> tuple[list[CanonicalKnowledgeItem], dict[str, str], list[list[DocumentKnowledgeCandidate]]]:
        parent = {candidate.candidate_item_id: candidate.candidate_item_id for candidate in candidates}

        def find(item_id: str) -> str:
            root = parent[item_id]
            if root != item_id:
                parent[item_id] = find(root)
            return parent[item_id]

        def union(left: str, right: str) -> None:
            left_root = find(left)
            right_root = find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        for match_candidate in match_candidates:
            if match_candidate.suggested_action not in {"merge", "replace"}:
                continue
            source_ids = match_candidate.source_candidate_item_ids
            if len(source_ids) == 2 and all(item_id in parent for item_id in source_ids):
                union(source_ids[0], source_ids[1])

        grouped: dict[str, list[DocumentKnowledgeCandidate]] = defaultdict(list)
        for candidate in candidates:
            grouped[find(candidate.candidate_item_id)].append(candidate)

        canonical_items: list[CanonicalKnowledgeItem] = []
        candidate_to_object_id: dict[str, str] = {}
        canonical_groups: list[list[DocumentKnowledgeCandidate]] = []
        for group in grouped.values():
            group = sorted(group, key=lambda item: (item.display_name, item.document_id, item.candidate_item_id))
            source_candidate_ids = [candidate.candidate_item_id for candidate in group]
            identity_key = self._identity_key(group[0])
            knowledge_id = f"CK-{short_identity_hash([group[0].archive_id, identity_key.identity_key_id, source_candidate_ids])}"
            for candidate_id in source_candidate_ids:
                candidate_to_object_id[candidate_id] = knowledge_id
            source_document_ids = self._unique_strings(candidate.document_id for candidate in group)
            evidence_refs = self._unique_artifact_refs(ref for candidate in group for ref in candidate.evidence_refs)
            relation_refs = self._unique_strings(ref for candidate in group for ref in candidate.relation_refs)
            aliases = self._unique_strings(alias for candidate in group for alias in candidate.aliases)
            explicit_definition_count = sum(1 for candidate in group if candidate.has_explicit_definition)
            canonical_items.append(
                CanonicalKnowledgeItem(
                    knowledge_id=knowledge_id,
                    identity_key=identity_key,
                    status="candidate",
                    display_name=self._display_name(group),
                    aliases=aliases,
                    source_document_ids=source_document_ids,
                    source_candidate_item_ids=source_candidate_ids,
                    evidence_refs=evidence_refs,
                    relation_refs=relation_refs,
                    version="candidate-v1",
                    quality_summary={
                        "source_document_count": len(source_document_ids),
                        "evidence_count": len(evidence_refs),
                        "explicit_definition_count": explicit_definition_count,
                        "candidate_only": True,
                    },
                )
            )
            canonical_groups.append(group)
        return sorted(canonical_items, key=lambda item: item.knowledge_id), candidate_to_object_id, canonical_groups

    def _build_resolved_objects(
        self,
        grouped_candidates: list[list[DocumentKnowledgeCandidate]],
        match_candidates: list[CrossDocumentMatchCandidate],
        *,
        update_plan: KnowledgeUpdatePlan | None,
    ) -> list[ResolvedKnowledgeObject]:
        conflict_reasons_by_candidate: dict[str, list[str]] = defaultdict(list)
        scores_by_candidate: dict[str, list[float]] = defaultdict(list)
        actions_by_candidate: dict[str, list[str]] = defaultdict(list)
        for match_candidate in match_candidates:
            for candidate_id in match_candidate.source_candidate_item_ids:
                scores_by_candidate[candidate_id].append(match_candidate.similarity_score)
                actions_by_candidate[candidate_id].append(match_candidate.suggested_action)
                if match_candidate.suggested_action == "mark_conflict":
                    conflict_reasons_by_candidate[candidate_id].append(
                        match_candidate.explanation or "same identity with divergent definitions"
                    )

        stale_ids = set(update_plan.stale_object_ids if update_plan else [])
        affected_knowledge_ids = set(update_plan.affected_knowledge_ids if update_plan else [])
        resolved_objects: list[ResolvedKnowledgeObject] = []

        for group in grouped_candidates:
            group = sorted(group, key=lambda item: (item.display_name, item.document_id, item.candidate_item_id))
            source_candidate_ids = [candidate.candidate_item_id for candidate in group]
            identity_key = self._identity_key(group[0])
            object_id = f"CK-{short_identity_hash([group[0].archive_id, identity_key.identity_key_id, source_candidate_ids])}"
            source_document_ids = self._unique_strings(candidate.document_id for candidate in group)
            evidence_refs = self._unique_artifact_refs(ref for candidate in group for ref in candidate.evidence_refs)
            aliases = self._unique_strings(alias for candidate in group for alias in candidate.aliases)
            explicit_definition_count = sum(1 for candidate in group if candidate.has_explicit_definition)
            match_scores = [score for candidate_id in source_candidate_ids for score in scores_by_candidate[candidate_id]]
            conflict_reasons = [
                *[
                    reason
                    for candidate_id in source_candidate_ids
                    for reason in conflict_reasons_by_candidate[candidate_id]
                ],
                *[reason for candidate in group for reason in candidate.conflict_reasons],
            ]
            has_rule_conflict = any(candidate.conflict_reasons for candidate in group)
            confidence = self._object_confidence(
                source_document_count=len(source_document_ids),
                evidence_count=len(evidence_refs),
                relation_count=len(self._unique_strings(ref for candidate in group for ref in candidate.relation_refs)),
                match_scores=match_scores,
                has_conflict=bool(conflict_reasons),
            )
            conflict_status = self._object_conflict_status(
                object_id=object_id,
                source_candidate_ids=source_candidate_ids,
                confidence=confidence,
                has_match_conflict=bool(conflict_reasons_by_candidate) and any(
                    conflict_reasons_by_candidate[candidate_id] for candidate_id in source_candidate_ids
                ),
                has_rule_conflict=has_rule_conflict,
                stale_ids=stale_ids,
                affected_knowledge_ids=affected_knowledge_ids,
            )
            merge_decision = self._object_merge_decision(
                source_candidate_ids=source_candidate_ids,
                actions=[action for candidate_id in source_candidate_ids for action in actions_by_candidate[candidate_id]],
                conflict_status=conflict_status,
            )
            trace_ids = [self._object_trace_id(object_id)]
            if conflict_status in {"conflict_pending", "rule_conflict"}:
                trace_ids.append(self._conflict_trace_id(object_id, source_candidate_ids))
            if conflict_status == "stale":
                trace_ids.append(self._stale_trace_id(object_id))

            resolved_objects.append(
                ResolvedKnowledgeObject(
                    object_id=object_id,
                    canonical_name=self._display_name(group),
                    object_type=group[0].object_type,
                    source_candidate_ids=source_candidate_ids,
                    source_document_ids=source_document_ids,
                    evidence_refs=evidence_refs,
                    confidence=confidence,
                    merge_decision=merge_decision,
                    conflict_status=conflict_status,
                    identity_key=identity_key,
                    aliases=aliases,
                    resolution_trace_ids=trace_ids,
                    quality_summary={
                        "source_document_count": len(source_document_ids),
                        "evidence_count": len(evidence_refs),
                        "explicit_definition_count": explicit_definition_count,
                        "candidate_only": True,
                        "conflict_reasons": self._unique_strings(conflict_reasons),
                        "heuristic_rules": [
                            "same normalized name or alias",
                            "AV/OV/SV view-number normalized name",
                            "definition, relation-neighborhood and evidence similarity",
                        ],
                    },
                )
            )

        return sorted(resolved_objects, key=lambda item: item.object_id)

    def _build_resolved_relations(
        self,
        candidate_relations: list[DocumentRelationCandidate],
        candidates: list[DocumentKnowledgeCandidate],
        resolved_objects: list[ResolvedKnowledgeObject],
        candidate_to_object_id: dict[str, str],
    ) -> tuple[list[ResolvedKnowledgeRelation], list[KnowledgeResolutionTrace]]:
        object_by_id = {item.object_id: item for item in resolved_objects}
        candidate_by_id = {candidate.candidate_item_id: candidate for candidate in candidates}
        local_index, global_index = self._build_candidate_name_indexes(candidates)
        relation_groups: dict[tuple[str, str, str], dict[str, Any]] = {}
        trace: list[KnowledgeResolutionTrace] = []

        for relation in candidate_relations:
            source_candidate_id = self._resolve_relation_endpoint(
                relation.source_name,
                relation.document_id,
                local_index,
                global_index,
                candidate_to_object_id,
            )
            target_candidate_id = self._resolve_relation_endpoint(
                relation.target_name,
                relation.document_id,
                local_index,
                global_index,
                candidate_to_object_id,
            )
            if not source_candidate_id or not target_candidate_id:
                trace.append(
                    KnowledgeResolutionTrace(
                        trace_id=f"TRACE-SKIP-{short_identity_hash([relation.relation_candidate_id, relation.source_name, relation.target_name])}",
                        trace_type="relation_skipped",
                        source_candidate_ids=[
                            candidate_id for candidate_id in [source_candidate_id, target_candidate_id] if candidate_id
                        ],
                        rule_execution_record_ids=list(relation.source_rule_execution_ids),
                        evidence_refs=list(relation.evidence_refs),
                        reason="relation endpoint could not be mapped to a resolved knowledge object",
                        metadata={
                            "relation_candidate_id": relation.relation_candidate_id,
                            "source_name": relation.source_name,
                            "target_name": relation.target_name,
                            "document_id": relation.document_id,
                        },
                    )
                )
                continue

            source_object_id = candidate_to_object_id[source_candidate_id]
            target_object_id = candidate_to_object_id[target_candidate_id]
            if source_object_id == target_object_id:
                trace.append(
                    KnowledgeResolutionTrace(
                        trace_id=f"TRACE-SKIP-{short_identity_hash([relation.relation_candidate_id, source_object_id])}",
                        trace_type="relation_skipped",
                        object_ids=[source_object_id],
                        source_candidate_ids=[source_candidate_id, target_candidate_id],
                        rule_execution_record_ids=list(relation.source_rule_execution_ids),
                        evidence_refs=list(relation.evidence_refs),
                        reason="relation endpoints collapsed into the same resolved object after merge",
                        metadata={"relation_candidate_id": relation.relation_candidate_id},
                    )
                )
                continue

            key = (source_object_id, target_object_id, relation.relation_type)
            row = relation_groups.setdefault(
                key,
                {
                    "candidate_relation_ids": [],
                    "document_ids": [],
                    "evidence_refs": [],
                    "confidence_values": [],
                    "source_candidate_ids": [],
                    "rule_execution_ids": [],
                },
            )
            row["candidate_relation_ids"].append(relation.relation_candidate_id)
            row["document_ids"].append(relation.document_id)
            row["evidence_refs"].extend(relation.evidence_refs)
            row["source_candidate_ids"].extend([source_candidate_id, target_candidate_id])
            row["rule_execution_ids"].extend(relation.source_rule_execution_ids)
            relation_confidence = relation.confidence
            if relation_confidence is None:
                source_confidence = object_by_id[source_object_id].confidence
                target_confidence = object_by_id[target_object_id].confidence
                relation_confidence = round(min(source_confidence, target_confidence) * 0.88, 3)
            row["confidence_values"].append(relation_confidence)
            if relation.evidence_refs:
                row["confidence_values"].append(min(relation_confidence + 0.04, 1.0))

        resolved_relations: list[ResolvedKnowledgeRelation] = []
        for (source_object_id, target_object_id, relation_type), row in relation_groups.items():
            candidate_relation_ids = self._unique_strings(row["candidate_relation_ids"])
            document_ids = self._unique_strings(row["document_ids"])
            evidence_refs = self._unique_artifact_refs(row["evidence_refs"])
            confidence = min(max(row["confidence_values"] or [0.62]) + 0.03 * max(len(document_ids) - 1, 0), 0.99)
            relation_id = f"REL-{short_identity_hash([source_object_id, target_object_id, relation_type, candidate_relation_ids])}"
            trace_id = self._relation_trace_id(relation_id)
            resolved_relations.append(
                ResolvedKnowledgeRelation(
                    relation_id=relation_id,
                    source_object_id=source_object_id,
                    target_object_id=target_object_id,
                    relation_type=relation_type,
                    evidence_refs=evidence_refs,
                    confidence=round(confidence, 3),
                    source_candidate_relation_ids=candidate_relation_ids,
                    source_document_ids=document_ids,
                    resolution_trace_ids=[trace_id],
                )
            )
            trace.append(
                KnowledgeResolutionTrace(
                    trace_id=trace_id,
                    trace_type="relation_resolution",
                    object_ids=[source_object_id, target_object_id],
                    relation_ids=[relation_id],
                    source_candidate_ids=self._unique_strings(row["source_candidate_ids"]),
                    rule_execution_record_ids=self._unique_strings(row["rule_execution_ids"]),
                    evidence_refs=evidence_refs,
                    reason="candidate relations were mapped onto resolved source and target knowledge objects",
                    metadata={
                        "relation_type": relation_type,
                        "source_document_ids": document_ids,
                        "source_candidate_relation_ids": candidate_relation_ids,
                    },
                )
            )

        return sorted(resolved_relations, key=lambda item: item.relation_id), trace

    def _build_resolution_trace(
        self,
        resolved_objects: list[ResolvedKnowledgeObject],
        resolved_relations: list[ResolvedKnowledgeRelation],
        match_candidates: list[CrossDocumentMatchCandidate],
        merge_decisions: list[KnowledgeMergeDecision],
        relation_trace: list[KnowledgeResolutionTrace],
        *,
        update_plan: KnowledgeUpdatePlan | None,
    ) -> list[KnowledgeResolutionTrace]:
        traces: list[KnowledgeResolutionTrace] = []
        decision_by_match_id = {
            match_id: decision
            for decision in merge_decisions
            for match_id in decision.candidate_ids
        }
        object_by_candidate: dict[str, ResolvedKnowledgeObject] = {}
        for resolved_object in resolved_objects:
            for candidate_id in resolved_object.source_candidate_ids:
                object_by_candidate[candidate_id] = resolved_object
            traces.append(
                KnowledgeResolutionTrace(
                    trace_id=self._object_trace_id(resolved_object.object_id),
                    trace_type="object_resolution",
                    object_ids=[resolved_object.object_id],
                    source_candidate_ids=resolved_object.source_candidate_ids,
                    evidence_refs=resolved_object.evidence_refs,
                    reason=(
                        f"{resolved_object.merge_decision} object with "
                        f"{len(resolved_object.source_document_ids)} source documents and "
                        f"confidence={resolved_object.confidence:.2f}"
                    ),
                    metadata={
                        "canonical_name": resolved_object.canonical_name,
                        "object_type": resolved_object.object_type,
                        "conflict_status": resolved_object.conflict_status,
                    },
                )
            )

        for match_candidate in match_candidates:
            related_object_ids = self._unique_strings(
                object_by_candidate[candidate_id].object_id
                for candidate_id in match_candidate.source_candidate_item_ids
                if candidate_id in object_by_candidate
            )
            decision = decision_by_match_id.get(match_candidate.candidate_id)
            trace_type: Literal["merge_decision", "conflict"] = (
                "conflict" if match_candidate.suggested_action == "mark_conflict" else "merge_decision"
            )
            traces.append(
                KnowledgeResolutionTrace(
                    trace_id=f"TRACE-MATCH-{short_identity_hash([match_candidate.candidate_id, match_candidate.suggested_action])}",
                    trace_type=trace_type,
                    object_ids=related_object_ids,
                    source_candidate_ids=match_candidate.source_candidate_item_ids,
                    rule_execution_record_ids=decision.rule_execution_record_ids if decision else [],
                    evidence_refs=match_candidate.evidence_refs,
                    reason=match_candidate.explanation or self._decision_reason(match_candidate),
                    metadata={
                        "match_candidate_id": match_candidate.candidate_id,
                        "similarity_score": match_candidate.similarity_score,
                        "suggested_action": match_candidate.suggested_action,
                        "match_features": match_candidate.match_features,
                    },
                )
            )
            if match_candidate.suggested_action == "mark_conflict":
                for object_id in related_object_ids:
                    source_candidate_ids = [
                        candidate_id
                        for candidate_id in match_candidate.source_candidate_item_ids
                        if object_by_candidate.get(candidate_id)
                        and object_by_candidate[candidate_id].object_id == object_id
                    ]
                    traces.append(
                        KnowledgeResolutionTrace(
                            trace_id=self._conflict_trace_id(object_id, source_candidate_ids),
                            trace_type="conflict",
                            object_ids=[object_id],
                            source_candidate_ids=source_candidate_ids,
                            rule_execution_record_ids=decision.rule_execution_record_ids if decision else [],
                            evidence_refs=match_candidate.evidence_refs,
                            reason="same-name candidates were retained separately because definitions or evidence diverged",
                            metadata={"match_candidate_id": match_candidate.candidate_id},
                        )
                    )

        traces.extend(relation_trace)
        if update_plan:
            affected_object_ids = [
                resolved_object.object_id
                for resolved_object in resolved_objects
                if resolved_object.object_id in update_plan.affected_knowledge_ids
                or set(resolved_object.source_candidate_ids).intersection(update_plan.stale_object_ids)
            ]
            for object_id in affected_object_ids:
                traces.append(
                    KnowledgeResolutionTrace(
                        trace_id=self._stale_trace_id(object_id),
                        trace_type="stale_update",
                        object_ids=[object_id],
                        reason="incremental rebuild impact set marks this resolved knowledge object as stale or affected",
                        metadata={
                            "update_plan_id": update_plan.update_plan_id,
                            "minimum_rebuild_stage_id": update_plan.minimum_rebuild_stage_id,
                            "writes_official_knowledge": update_plan.writes_official_knowledge,
                        },
                    )
                )

        return self._dedupe_traces(traces)

    def _build_update_plan(
        self,
        archive_id: str,
        canonical_items: list[CanonicalKnowledgeItem],
        *,
        generated_at: str,
    ) -> KnowledgeUpdatePlan | None:
        latest_task = self._load_latest_incremental_task(archive_id)
        if latest_task is None:
            return None

        impact_set = latest_task.get("impact_set") or {}
        stale_object_ids = self._unique_strings(
            [
                *self._as_string_list(impact_set.get("affected_candidate_ids") or impact_set.get("affected_candidates")),
                *self._as_string_list(impact_set.get("affected_relation_ids") or impact_set.get("affected_relations")),
                *self._as_string_list(
                    impact_set.get("affected_publication_snapshot_ids")
                    or impact_set.get("affected_publication_snapshots")
                ),
            ]
        )
        affected_candidate_ids = set(
            self._as_string_list(impact_set.get("affected_candidate_ids") or impact_set.get("affected_candidates"))
        )
        affected_knowledge_ids = [
            item.knowledge_id
            for item in canonical_items
            if affected_candidate_ids.intersection(set(item.source_candidate_item_ids))
        ]
        minimum_rebuild_stage_id = str(
            impact_set.get("minimum_rebuild_stage_id")
            or latest_task.get("minimum_rebuild_stage_id")
            or latest_task.get("start_stage_id")
            or "candidate_resolution"
        )
        impact_id = str(impact_set.get("impact_id") or impact_set.get("impact_set_id") or latest_task.get("task_id"))
        return KnowledgeUpdatePlan(
            update_plan_id=f"KUP-{short_identity_hash([archive_id, impact_id, stale_object_ids])}",
            archive_id=archive_id,
            minimum_rebuild_stage_id=minimum_rebuild_stage_id,
            stale_object_ids=stale_object_ids,
            affected_knowledge_ids=affected_knowledge_ids,
            impacted_relation_ids=self._as_string_list(
                impact_set.get("affected_relation_ids") or impact_set.get("affected_relations")
            ),
            recommended_actions=[
                f"recompute candidates from {minimum_rebuild_stage_id}",
                "write new_runtime_candidates only",
                "keep formal knowledge unchanged until governance confirmation",
            ],
            requires_governance_confirmation=bool(latest_task.get("writes_official_knowledge") is not False),
            writes_official_knowledge=False,
            generated_at=generated_at,
        )

    def _identity_key(
        self,
        candidate: DocumentKnowledgeCandidate,
        other: DocumentKnowledgeCandidate | None = None,
    ) -> KnowledgeIdentityKey:
        candidates = [candidate, *(list([other]) if other is not None else [])]
        normalized_names = [normalize_identity_text(item.display_name) for item in candidates]
        alias_tokens = self._unique_strings(
            normalize_identity_text(alias)
            for item in candidates
            for alias in item.aliases
            if normalize_identity_text(alias)
        )
        relation_terms = self._unique_strings(term for item in candidates for term in item.relation_terms)
        definition_values = [normalize_identity_text(item.definition) for item in candidates if item.has_explicit_definition and item.definition]
        definition_signature = short_identity_hash(definition_values, length=16) if definition_values else None
        policy_snapshot_id = self._policy_snapshot_from_rule_ids(
            rule_id for item in candidates for rule_id in item.source_rule_execution_ids
        )
        key_payload = {
            "archive_id": candidate.archive_id,
            "knowledge_type": candidate.object_type,
            "normalized_name": normalized_names[0],
            "category": candidate.category,
            "business_scope": candidate.source_archive,
        }
        return KnowledgeIdentityKey(
            identity_key_id=f"IK-{short_identity_hash(key_payload)}",
            knowledge_type=candidate.object_type,
            normalized_name=normalized_names[0],
            business_scope=candidate.source_archive,
            key_fields={
                "category": candidate.category,
                "primary_name": normalized_names[0],
                "alias_tokens": "|".join(alias_tokens),
                "relation_terms": "|".join(relation_terms),
            },
            alias_tokens=alias_tokens,
            definition_signature=definition_signature,
            relation_neighborhood_hash=short_identity_hash(relation_terms, length=16) if relation_terms else None,
            policy_snapshot_id=policy_snapshot_id,
            generated_by_rule_execution_id=self._first_rule_execution_id(candidates),
        )

    def _match_features(
        self,
        left: DocumentKnowledgeCandidate,
        right: DocumentKnowledgeCandidate,
    ) -> dict[str, float]:
        return {
            "name_score": self._name_score(left, right),
            "definition_score": self._definition_score(left.definition, right.definition),
            "relation_score": self._set_similarity(left.relation_terms, right.relation_terms, neutral=0.62),
            "evidence_overlap_score": self._evidence_score(left.evidence_refs, right.evidence_refs),
            "view_number_score": self._view_number_score(left, right),
        }

    def _view_number_score(self, left: DocumentKnowledgeCandidate, right: DocumentKnowledgeCandidate) -> float:
        left_names = {self._strip_view_tokens(name) for name in self._identity_name_tokens(left)}
        right_names = {self._strip_view_tokens(name) for name in self._identity_name_tokens(right)}
        left_names.discard("")
        right_names.discard("")
        if not left_names or not right_names:
            return 0.0
        if left_names.intersection(right_names):
            return 1.0
        best = max(self._text_similarity(left_name, right_name) for left_name in left_names for right_name in right_names)
        left_view = self._view_family(left)
        right_view = self._view_family(right)
        if left_view and right_view and left_view != right_view and best >= 0.76:
            return round(min(best + 0.1, 1.0), 3)
        return round(best, 3)

    def _identity_name_tokens(self, candidate: DocumentKnowledgeCandidate) -> set[str]:
        names = {
            normalize_identity_text(candidate.display_name),
            self._strip_view_tokens(candidate.display_name),
            *[normalize_identity_text(alias) for alias in candidate.aliases],
            *[self._strip_view_tokens(alias) for alias in candidate.aliases],
        }
        return {name for name in names if name}

    def _strip_view_tokens(self, value: Any) -> str:
        normalized = normalize_identity_text(value)
        without_view = VIEW_TOKEN_RE.sub(" ", normalized)
        without_view = re.sub(r"\b(?:mid|far|near|as is|to be|term|version|v)\b", " ", without_view)
        return " ".join(without_view.split())

    def _view_family(self, candidate: DocumentKnowledgeCandidate | DocumentRelationCandidate) -> str | None:
        text = normalize_identity_text(
            " ".join(
                [
                    getattr(candidate, "document_id", ""),
                    getattr(candidate, "document_title", ""),
                    getattr(candidate, "display_name", ""),
                    getattr(candidate, "source_name", ""),
                    getattr(candidate, "target_name", ""),
                ]
            )
        )
        for view in ["av", "ov", "sv", "tv"]:
            if re.search(rf"\b{view}\s*[- ]?\s*\d+", text):
                return view.upper()
        return None

    def _suggest_action(
        self,
        left: DocumentKnowledgeCandidate,
        right: DocumentKnowledgeCandidate,
        features: dict[str, float],
        score: float,
    ) -> Literal["merge", "keep_separate", "replace", "mark_conflict"] | None:
        if left.object_type != right.object_type:
            return None
        if normalize_identity_text(left.category) != normalize_identity_text(right.category):
            if features["name_score"] < 0.92:
                return None
        both_explicit_definitions = left.has_explicit_definition and right.has_explicit_definition
        if both_explicit_definitions and features["name_score"] >= 0.9 and features["definition_score"] <= 0.58:
            return "mark_conflict"
        if (
            not both_explicit_definitions
            and features["name_score"] >= 0.98
            and features["view_number_score"] >= 0.92
        ):
            return "merge"
        if score >= 0.72 and (features["name_score"] >= 0.76 or features["view_number_score"] >= 0.92):
            return "merge"
        if features["name_score"] >= 0.92 and features["view_number_score"] >= 0.92 and score >= 0.68:
            return "merge"
        if score >= 0.58 and (features["name_score"] >= 0.7 or features["view_number_score"] >= 0.82):
            return "keep_separate"
        return None

    def _name_score(self, left: DocumentKnowledgeCandidate, right: DocumentKnowledgeCandidate) -> float:
        left_names = self._identity_name_tokens(left)
        right_names = self._identity_name_tokens(right)
        left_names.discard("")
        right_names.discard("")
        if left_names.intersection(right_names):
            return 1.0
        return round(max(self._text_similarity(left_name, right_name) for left_name in left_names for right_name in right_names), 3)

    def _build_candidate_name_indexes(
        self,
        candidates: list[DocumentKnowledgeCandidate],
    ) -> tuple[dict[tuple[str, str], list[str]], dict[str, list[str]]]:
        local_index: dict[tuple[str, str], list[str]] = defaultdict(list)
        global_index: dict[str, list[str]] = defaultdict(list)
        for candidate in candidates:
            for name in self._identity_name_tokens(candidate):
                local_index[(candidate.document_id, name)].append(candidate.candidate_item_id)
                global_index[name].append(candidate.candidate_item_id)
        return local_index, global_index

    def _resolve_relation_endpoint(
        self,
        endpoint_name: str,
        document_id: str,
        local_index: dict[tuple[str, str], list[str]],
        global_index: dict[str, list[str]],
        candidate_to_object_id: dict[str, str],
    ) -> str | None:
        endpoint_tokens = {
            normalize_identity_text(endpoint_name),
            self._strip_view_tokens(endpoint_name),
        }
        endpoint_tokens.discard("")
        for token in endpoint_tokens:
            local_matches = self._unique_strings(local_index.get((document_id, token), []))
            if len(local_matches) == 1:
                return local_matches[0]
            if len(local_matches) > 1:
                unique_objects = {candidate_to_object_id.get(candidate_id) for candidate_id in local_matches}
                if len(unique_objects) == 1:
                    return local_matches[0]
        for token in endpoint_tokens:
            global_matches = self._unique_strings(global_index.get(token, []))
            unique_objects = {candidate_to_object_id.get(candidate_id) for candidate_id in global_matches}
            unique_objects.discard(None)
            if len(unique_objects) == 1 and global_matches:
                return global_matches[0]
        return None

    def _object_confidence(
        self,
        *,
        source_document_count: int,
        evidence_count: int,
        relation_count: int,
        match_scores: list[float],
        has_conflict: bool,
    ) -> float:
        confidence = 0.58
        confidence += min(source_document_count, 4) * 0.06
        confidence += min(evidence_count, 5) * 0.035
        confidence += min(relation_count, 4) * 0.02
        if source_document_count > 1 and evidence_count >= source_document_count:
            confidence += 0.08
        if match_scores:
            confidence += max(match_scores) * 0.12
        if has_conflict:
            confidence -= 0.18
        return round(min(max(confidence, 0.05), 0.99), 3)

    @staticmethod
    def _object_conflict_status(
        *,
        object_id: str,
        source_candidate_ids: list[str],
        confidence: float,
        has_match_conflict: bool,
        has_rule_conflict: bool,
        stale_ids: set[str],
        affected_knowledge_ids: set[str],
    ) -> Literal["clean", "conflict_pending", "low_confidence", "stale", "rule_conflict"]:
        if has_rule_conflict:
            return "rule_conflict"
        if has_match_conflict:
            return "conflict_pending"
        if object_id in affected_knowledge_ids or stale_ids.intersection(source_candidate_ids):
            return "stale"
        if confidence < 0.66:
            return "low_confidence"
        return "clean"

    @staticmethod
    def _object_merge_decision(
        *,
        source_candidate_ids: list[str],
        actions: list[str],
        conflict_status: str,
    ) -> Literal["single_source", "merged", "kept_separate", "replaced", "conflict_pending"]:
        if conflict_status in {"conflict_pending", "rule_conflict"}:
            return "conflict_pending"
        if "replace" in actions:
            return "replaced"
        if len(source_candidate_ids) > 1:
            return "merged"
        if "keep_separate" in actions:
            return "kept_separate"
        return "single_source"

    @staticmethod
    def _object_trace_id(object_id: str) -> str:
        return f"TRACE-OBJ-{short_identity_hash(object_id)}"

    @staticmethod
    def _relation_trace_id(relation_id: str) -> str:
        return f"TRACE-REL-{short_identity_hash(relation_id)}"

    @staticmethod
    def _conflict_trace_id(object_id: str, source_candidate_ids: list[str]) -> str:
        return f"TRACE-CONFLICT-{short_identity_hash([object_id, source_candidate_ids])}"

    @staticmethod
    def _stale_trace_id(object_id: str) -> str:
        return f"TRACE-STALE-{short_identity_hash(object_id)}"

    def _definition_score(self, left: str | None, right: str | None) -> float:
        if not left or not right:
            return 0.62
        return round(max(self._text_similarity(left, right), self._token_similarity(left, right)), 3)

    def _evidence_score(self, left: tuple[ArtifactRef, ...], right: tuple[ArtifactRef, ...]) -> float:
        if not left or not right:
            return 0.56
        left_text = " ".join(ref.summary or ref.artifact_id for ref in left)
        right_text = " ".join(ref.summary or ref.artifact_id for ref in right)
        return round(max(self._text_similarity(left_text, right_text), self._token_similarity(left_text, right_text)), 3)

    def _contract_impact_set(self, archive_id: str, task: dict[str, Any]) -> ImpactSet:
        impact_set = task.get("impact_set") or {}
        impact_id = str(impact_set.get("impact_id") or impact_set.get("impact_set_id") or task.get("task_id") or "")
        affected_candidate_ids = self._as_string_list(
            impact_set.get("affected_candidate_ids") or impact_set.get("affected_candidates")
        )
        return ImpactSet(
            impact_set_id=impact_id,
            archive_id=archive_id,
            policy_package_version_id=str(
                impact_set.get("target_policy_snapshot_id")
                or impact_set.get("policy_package_version_id")
                or "candidate-policy"
            ),
            previous_policy_package_version_id=str(
                impact_set.get("source_policy_snapshot_id")
                or impact_set.get("previous_policy_package_version_id")
                or "previous-policy"
            ),
            changed_rule_ids=self._as_string_list(impact_set.get("changed_rule_ids")),
            affected_stage_ids=self._as_string_list(impact_set.get("affected_stage_ids") or impact_set.get("affected_stages")),
            affected_chunk_ids=self._as_string_list(impact_set.get("affected_chunk_ids") or impact_set.get("affected_chunks")),
            affected_candidate_ids=affected_candidate_ids,
            minimum_rebuild_stage_id=str(
                impact_set.get("minimum_rebuild_stage_id")
                or task.get("minimum_rebuild_stage_id")
                or task.get("start_stage_id")
                or "candidate_resolution"
            ),
            affected_document_ids=self._as_string_list(
                impact_set.get("affected_document_ids") or impact_set.get("affected_docs")
            ),
            affected_object_ids=self._unique_strings(
                [
                    *affected_candidate_ids,
                    *self._as_string_list(impact_set.get("affected_object_ids")),
                ]
            ),
            affected_relation_ids=self._as_string_list(
                impact_set.get("affected_relation_ids") or impact_set.get("affected_relations")
            ),
            affected_publication_snapshot_ids=self._as_string_list(
                impact_set.get("affected_publication_snapshot_ids")
                or impact_set.get("affected_publication_snapshots")
            ),
            requires_governance_reconfirmation=False,
            generated_at=str(impact_set.get("generated_at") or task.get("created_at") or datetime.now(UTC).isoformat()),
            writes_official_knowledge=bool(task.get("writes_official_knowledge", False)),
        )

    def _build_evidence_refs(self, document_id: str, local_item_id: str, evidence: Any) -> list[ArtifactRef]:
        evidence_rows = evidence if isinstance(evidence, list) else ([evidence] if evidence else [])
        refs = []
        for index, row in enumerate(evidence_rows, start=1):
            if isinstance(row, dict):
                row_document_id = str(row.get("document_id") or document_id)
                summary = str(
                    row.get("excerpt")
                    or row.get("summary")
                    or row.get("text")
                    or row.get("content")
                    or row.get("evidence")
                    or ""
                )[:240]
                artifact_id = str(row.get("artifact_id") or row.get("anchor_id") or f"{row_document_id}:{local_item_id}:evidence:{index}")
                metadata = {key: value for key, value in row.items() if key not in {"excerpt", "summary", "text", "content"}}
            else:
                row_document_id = document_id
                summary = str(row)[:240]
                artifact_id = f"{document_id}:{local_item_id}:evidence:{index}"
                metadata = {}
            refs.append(
                ArtifactRef(
                    artifact_id=artifact_id,
                    artifact_type="source_anchor",
                    document_id=row_document_id,
                    summary=summary or None,
                    metadata=metadata,
                )
            )
        return refs

    def _knowledge_object_type(self, collection_type: str, item: dict[str, Any]) -> str:
        text = normalize_identity_text(
            " ".join(
                [
                    collection_type,
                    str(item.get("category") or ""),
                    str(item.get("name") or item.get("display_name") or ""),
                    " ".join(self._as_unique_strings(item.get("aliases", []))),
                ]
            )
        )
        if collection_type in {"event", "process", "capability", "system", "node", "information_exchange"}:
            return collection_type
        if any(token in text for token in ["能力", "capability"]):
            return "capability"
        if any(token in text for token in ["系统", "体系", "service", "system"]):
            return "system"
        if any(token in text for token in ["节点", "node"]):
            return "node"
        if any(token in text for token in ["信息交换", "information exchange", "exchange"]):
            return "information_exchange"
        return collection_type or "entity"

    def _normalize_relation_type(self, value: Any) -> str:
        normalized = normalize_identity_text(value)
        if any(token in normalized for token in ["part of", "composed", "composition", "contains", "包含", "组成"]):
            return "composition"
        if any(token in normalized for token in ["execute", "perform", "执行"]):
            return "execution"
        if any(token in normalized for token in ["support", "supports", "支撑", "支持"]):
            return "support"
        if any(token in normalized for token in ["exchange", "flow", "interface", "交换", "交互", "接口"]):
            return "exchange"
        if any(token in normalized for token in ["depend", "requires", "uses", "依赖", "使用"]):
            return "dependency"
        if any(token in normalized for token in ["map", "mapping", "trace", "映射", "对应"]):
            return "mapping"
        if any(token in normalized for token in ["constraint", "constrain", "限制", "约束"]):
            return "constraint"
        return normalized.replace(" ", "_") or "related_to"

    def _collect_item_conflict_reasons(self, item: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        status = normalize_identity_text(item.get("conflict_status") or item.get("status") or "")
        if status in {"conflict", "conflict pending", "rule conflict", "blocked"}:
            reasons.append(str(item.get("conflict_reason") or item.get("reason") or status))
        for key in ["conflict_reason", "rule_conflict_reason", "rule_conflict"]:
            value = item.get(key)
            if isinstance(value, str) and value:
                reasons.append(value)
            elif value is True:
                reasons.append(key)
        return self._unique_strings(reasons)

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return min(max(float(value), 0.0), 1.0)
        if isinstance(value, str):
            try:
                return min(max(float(value), 0.0), 1.0)
            except ValueError:
                return None
        return None

    def _relation_neighborhood(
        self,
        contribution: dict[str, Any],
        item: dict[str, Any],
        document_id: str,
    ) -> tuple[list[str], list[str]]:
        item_names = {
            normalize_identity_text(item.get("name")),
            *[normalize_identity_text(alias) for alias in self._as_unique_strings(item.get("aliases", []))],
        }
        item_names.discard("")
        relation_terms: list[str] = []
        relation_refs: list[str] = []
        for index, relation in enumerate(contribution.get("relations", []), start=1):
            if not isinstance(relation, dict):
                continue
            source_name = normalize_identity_text(relation.get("source_name") or relation.get("source") or relation.get("from"))
            target_name = normalize_identity_text(relation.get("target_name") or relation.get("target") or relation.get("to"))
            relation_type = self._normalize_relation_type(relation.get("type") or relation.get("relation_type") or "related_to")
            touches_source = source_name in item_names
            touches_target = target_name in item_names
            if not touches_source and not touches_target:
                continue
            other_name = target_name if touches_source else source_name
            relation_terms.append(f"{relation_type}:{other_name}")
            relation_refs.append(str(relation.get("id") or f"{document_id}:relation:{index}"))
        return self._unique_strings(relation_terms), self._unique_strings(relation_refs)

    def _definition_text(self, item: dict[str, Any], evidence_refs: tuple[ArtifactRef, ...]) -> str | None:
        explicit = item.get("definition") or item.get("description") or item.get("summary")
        if explicit:
            return str(explicit)
        summaries = [ref.summary for ref in evidence_refs if ref.summary]
        return " ".join(summaries) if summaries else None

    def _load_latest_incremental_task(self, archive_id: str) -> dict[str, Any] | None:
        task_dir = self.output_root / f"{archive_id}-incremental-rebuild-tasks"
        if not task_dir.exists():
            return None
        task_paths = [path for path in task_dir.glob("irt-*.json") if not path.name.endswith("-candidates.json")]
        if not task_paths:
            return None
        task_paths.sort(key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
        return json.loads(task_paths[0].read_text(encoding="utf-8"))

    def _policy_snapshot_id(self, contributions: list[dict[str, Any]]) -> str | None:
        for contribution in contributions:
            runtime_trace = ((contribution.get("extraction") or {}).get("runtime_trace") or {})
            for value in self._walk_values(runtime_trace):
                if isinstance(value, dict):
                    snapshot_id = value.get("snapshot_id") or value.get("policy_snapshot_id")
                    if snapshot_id:
                        return str(snapshot_id)
        return None

    def _policy_package_version_id(self, contributions: list[dict[str, Any]]) -> str | None:
        for contribution in contributions:
            runtime_trace = ((contribution.get("extraction") or {}).get("runtime_trace") or {})
            for value in self._walk_values(runtime_trace):
                if isinstance(value, dict):
                    version_id = (
                        value.get("policy_package_version_id")
                        or value.get("target_policy_snapshot_id")
                        or value.get("policy_version_id")
                    )
                    if version_id:
                        return str(version_id)
        return None

    def _policy_snapshot_from_rule_ids(self, rule_ids: Any) -> str | None:
        unique_rule_ids = self._unique_strings(rule_ids)
        return f"rules:{short_identity_hash(unique_rule_ids, length=10)}" if unique_rule_ids else None

    def _collect_rule_execution_ids(self, contribution: dict[str, Any]) -> list[str]:
        runtime_trace = ((contribution.get("extraction") or {}).get("runtime_trace") or {})
        record_ids = []
        for value in self._walk_values(runtime_trace):
            if not isinstance(value, dict):
                continue
            execution_id = value.get("execution_id")
            rule_id = value.get("rule_id")
            if execution_id:
                record_ids.append(str(execution_id))
            elif rule_id and value.get("input_hash") and value.get("output_hash"):
                record_ids.append(str(rule_id))
        return self._unique_strings(record_ids)

    def _walk_values(self, value: Any) -> list[Any]:
        values = [value]
        if isinstance(value, dict):
            for child in value.values():
                values.extend(self._walk_values(child))
        elif isinstance(value, list):
            for child in value:
                values.extend(self._walk_values(child))
        return values

    @staticmethod
    def _dedupe_traces(traces: list[KnowledgeResolutionTrace]) -> list[KnowledgeResolutionTrace]:
        result: list[KnowledgeResolutionTrace] = []
        seen: set[str] = set()
        for trace in traces:
            if trace.trace_id in seen:
                continue
            seen.add(trace.trace_id)
            result.append(trace)
        return sorted(result, key=lambda item: item.trace_id)

    def _input_document_ids(self, contributions: list[dict[str, Any]]) -> list[str]:
        return self._unique_strings((contribution.get("document") or {}).get("id") for contribution in contributions)

    def _match_explanation(self, action: str, features: dict[str, float]) -> str:
        return (
            f"suggested_action={action}; "
            f"name={features['name_score']:.2f}, definition={features['definition_score']:.2f}, "
            f"relation={features['relation_score']:.2f}, evidence={features['evidence_overlap_score']:.2f}, "
            f"view={features['view_number_score']:.2f}"
        )

    def _decision_reason(self, match_candidate: CrossDocumentMatchCandidate) -> str:
        if match_candidate.suggested_action == "merge":
            return "Identity key, alias/name evidence, and similarity features support merging candidate knowledge without writing formal knowledge."
        if match_candidate.suggested_action == "mark_conflict":
            return "Candidates point to the same identity but definition or evidence features diverge; keep for governance confirmation."
        if match_candidate.suggested_action == "replace":
            return "Candidate appears to revise an existing knowledge object; emit revision candidate only."
        return "Candidates are similar enough to review but not strong enough for automatic merge."

    @staticmethod
    def _decision_for_action(action: str) -> Literal["merged", "kept_separate", "replaced", "conflict_pending"]:
        if action == "merge":
            return "merged"
        if action == "replace":
            return "replaced"
        if action == "mark_conflict":
            return "conflict_pending"
        return "kept_separate"

    @staticmethod
    def _display_name(group: list[DocumentKnowledgeCandidate]) -> str:
        return max(group, key=lambda item: (len(item.evidence_refs), len(item.aliases), -len(item.display_name))).display_name

    @staticmethod
    def _first_rule_execution_id(candidates: list[DocumentKnowledgeCandidate]) -> str | None:
        for candidate in candidates:
            if candidate.source_rule_execution_ids:
                return candidate.source_rule_execution_ids[0]
        return None

    @staticmethod
    def _text_similarity(left: str, right: str) -> float:
        left_normalized = normalize_identity_text(left)
        right_normalized = normalize_identity_text(right)
        if not left_normalized or not right_normalized:
            return 0
        if left_normalized == right_normalized:
            return 1
        return SequenceMatcher(None, left_normalized, right_normalized).ratio()

    @staticmethod
    def _token_similarity(left: str, right: str) -> float:
        left_tokens = set(normalize_identity_text(left).split())
        right_tokens = set(normalize_identity_text(right).split())
        if not left_tokens or not right_tokens:
            return 0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    @staticmethod
    def _set_similarity(left: tuple[str, ...], right: tuple[str, ...], *, neutral: float) -> float:
        left_set = set(left)
        right_set = set(right)
        if not left_set or not right_set:
            return neutral
        return round(len(left_set & right_set) / len(left_set | right_set), 3)

    @staticmethod
    def _unique_artifact_refs(values: Any) -> list[ArtifactRef]:
        result: list[ArtifactRef] = []
        seen: set[str] = set()
        for value in values:
            key = value.artifact_id
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result

    @staticmethod
    def _as_unique_strings(value: Any) -> list[str]:
        if isinstance(value, list):
            return ArchiveKnowledgeResolutionService._unique_strings(str(item) for item in value if item)
        if isinstance(value, tuple):
            return ArchiveKnowledgeResolutionService._unique_strings(str(item) for item in value if item)
        if value:
            return [str(value)]
        return []

    @staticmethod
    def _as_string_list(value: Any) -> list[str]:
        return ArchiveKnowledgeResolutionService._as_unique_strings(value)

    @staticmethod
    def _unique_strings(values: Any) -> list[str]:
        result: list[str] = []
        for value in values:
            if value is None:
                continue
            normalized = str(value)
            if not normalized or normalized in result:
                continue
            result.append(normalized)
        return result
