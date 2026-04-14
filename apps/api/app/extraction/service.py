import json
import re
from pathlib import Path
from typing import Any

from app.config import settings
from app.extraction.chunking import DocumentChunk, build_document_chunks
from app.extraction.rules import extract_document_batch
from app.extraction.schema import (
    ExtractedCandidate,
    ExtractedRelation,
    ExtractionBatch,
    StructuredExtractionResponse,
)
from app.integrations.llm import build_structured_llm
from app.knowledge_builder import SourceDocument
from app.parsing.models import ParsedSegment


class ExtractionService:
    def __init__(self, *, formal_extraction_mode: bool = False) -> None:
        self.formal_extraction_mode = formal_extraction_mode

    def extract(self, segments: list[ParsedSegment]):
        return self.extract_document(
            document_id="ad-hoc-document",
            title="ad-hoc-document",
            file_path="ad-hoc-document.txt",
            segments=segments,
        ).candidates

    def extract_document(
        self,
        *,
        document_id: str,
        title: str,
        file_path: str,
        segments: list[ParsedSegment],
    ) -> ExtractionBatch:
        source_document = self._build_source_document(
            title=title,
            file_path=file_path,
            segments=segments,
        )
        if self._should_use_chunked_formal_extraction(segments):
            return self._extract_with_chunks(
                document_id=document_id,
                title=title,
                file_path=file_path,
                segments=segments,
                source_document=source_document,
            )
        return self._extract_standard_document(
            document_id=document_id,
            title=title,
            file_path=file_path,
            segments=segments,
            source_document=source_document,
        )

    @staticmethod
    def _build_source_document(
        *,
        title: str,
        file_path: str,
        segments: list[ParsedSegment],
    ) -> SourceDocument:
        return SourceDocument(
            path=file_path,
            title=title,
            file_type=Path(file_path).suffix.lstrip(".") or "txt",
            source_archive="runtime",
            text="\n".join(segment.content for segment in segments),
        )

    def _extract_standard_document(
        self,
        *,
        document_id: str,
        title: str,
        file_path: str,
        segments: list[ParsedSegment],
        source_document: SourceDocument,
    ) -> ExtractionBatch:
        base_batch = extract_document_batch(document_id=document_id, document=source_document, segments=segments)
        structured_llm_bundle = self._build_structured_llm_bundle()
        llm_batch = self._try_llm_enrichment(
            document_id=document_id,
            title=title,
            file_path=file_path,
            segments=segments,
            base_batch=base_batch,
            structured_llm_bundle=structured_llm_bundle,
        )
        return self._merge_standard_batches(
            document_id=document_id,
            title=title,
            base_batch=base_batch,
            llm_batch=llm_batch,
        )

    def _extract_with_chunks(
        self,
        *,
        document_id: str,
        title: str,
        file_path: str,
        segments: list[ParsedSegment],
        source_document: SourceDocument,
    ) -> ExtractionBatch:
        chunks = build_document_chunks(segments, max_chars=settings.formal_chunk_char_limit)
        structured_llm_bundle = self._build_structured_llm_bundle()
        chunk_batches = [
            self._extract_chunk_batch(
                document_id=document_id,
                title=title,
                file_path=file_path,
                source_document=source_document,
                chunk=chunk,
                structured_llm_bundle=structured_llm_bundle,
            )
            for chunk in chunks
        ]
        return self._merge_chunk_batches(
            document_id=document_id,
            title=title,
            chunks=chunks,
            chunk_batches=chunk_batches,
        )

    def _extract_chunk_batch(
        self,
        *,
        document_id: str,
        title: str,
        file_path: str,
        source_document: SourceDocument,
        chunk: DocumentChunk,
        structured_llm_bundle: tuple[Any, dict[str, str | None]] | None,
    ) -> ExtractionBatch:
        chunk_source_document = SourceDocument(
            path=source_document.path,
            title=source_document.title,
            file_type=source_document.file_type,
            source_archive=source_document.source_archive,
            text="\n".join(segment.content for segment in chunk.segments),
            parser_name=source_document.parser_name,
            segment_count=len(chunk.segments),
            segments=chunk.segments,
        )
        base_batch = self._attach_chunk_source(
            extract_document_batch(document_id=document_id, document=chunk_source_document, segments=chunk.segments),
            chunk=chunk,
        )
        llm_batch = self._try_llm_enrichment(
            document_id=document_id,
            title=title,
            file_path=file_path,
            segments=chunk.segments,
            base_batch=base_batch,
            structured_llm_bundle=structured_llm_bundle,
            sample_segments=False,
            scope_label=chunk.heading,
        )
        if llm_batch is not None:
            llm_batch = self._attach_chunk_source(llm_batch, chunk=chunk)

        merged_batch = self._merge_standard_batches(
            document_id=document_id,
            title=title,
            base_batch=base_batch,
            llm_batch=llm_batch,
        )
        merged_batch.metadata.update(
            {
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "chunk_heading": chunk.heading,
                "chunk_char_count": chunk.char_count,
                "chunk_segment_count": len(chunk.segments),
            }
        )
        return merged_batch

    def _build_structured_llm_bundle(self) -> tuple[Any, dict[str, str | None]] | None:
        if not (self.formal_extraction_mode or settings.llm_enrichment_enabled):
            return None
        try:
            return build_structured_llm(output_schema=StructuredExtractionResponse)
        except Exception as exc:
            if self.formal_extraction_mode:
                raise ValueError(f"正式知识库抽取要求使用结构化大模型抽取，但当前调用失败：{exc}") from exc
            return None

    def _try_llm_enrichment(
        self,
        *,
        document_id: str,
        title: str,
        file_path: str,
        segments: list[ParsedSegment],
        base_batch: ExtractionBatch,
        structured_llm_bundle: tuple[Any, dict[str, str | None]] | None,
        sample_segments: bool = True,
        scope_label: str | None = None,
    ) -> ExtractionBatch | None:
        del document_id
        if structured_llm_bundle is None:
            return None

        prompt = self._build_llm_prompt(
            title=title,
            file_path=file_path,
            segments=segments,
            base_batch=base_batch,
            scope_label=scope_label,
            sample_segments=sample_segments,
        )

        try:
            structured_llm, llm_metadata = structured_llm_bundle
            response = structured_llm.complete(prompt)
        except Exception as exc:
            if self.formal_extraction_mode:
                raise ValueError(f"正式知识库抽取要求使用结构化大模型抽取，但当前调用失败：{exc}") from exc
            return None

        result = getattr(response, "raw", response)
        if not isinstance(result, StructuredExtractionResponse):
            try:
                payload = getattr(response, "text", None) or getattr(response, "message", None) or result
                if isinstance(payload, StructuredExtractionResponse):
                    result = payload
                elif isinstance(payload, dict):
                    result = StructuredExtractionResponse.model_validate(payload)
                else:
                    result = StructuredExtractionResponse.model_validate_json(payload)
            except Exception as exc:
                if self.formal_extraction_mode:
                    raise ValueError(f"正式知识库抽取要求结构化大模型返回可解析结果，但当前响应无法通过 schema 校验：{exc}") from exc
                return None

        if self.formal_extraction_mode and (not llm_metadata.get("provider") or not llm_metadata.get("model")):
            raise ValueError("正式知识库抽取要求记录实际使用的大模型供应商与模型名称，但当前元数据缺失")

        return ExtractionBatch(
            document_id=base_batch.document_id,
            title=base_batch.title,
            strategy="llm_provider_adapter",
            candidates=[
                ExtractedCandidate(
                    item_type=item.item_type,
                    canonical_name=item.canonical_name.strip(),
                    confidence=item.confidence,
                    payload=self._normalize_payload(
                        {
                            "category": item.category,
                            "aliases": [alias.strip() for alias in item.aliases if alias.strip()],
                            "evidence": item.evidence,
                        }
                    ),
                )
                for item in result.candidates
                if item.canonical_name.strip()
            ],
            relations=[
                ExtractedRelation(
                    relation_type=relation.relation_type,
                    source_name=relation.source_name.strip(),
                    target_name=relation.target_name.strip(),
                    confidence=relation.confidence,
                    payload=self._normalize_payload({"evidence": relation.evidence}),
                )
                for relation in result.relations
                if relation.source_name.strip() and relation.target_name.strip()
            ],
            metadata={**llm_metadata, "notes": result.notes},
        )

    def _merge_standard_batches(
        self,
        *,
        document_id: str,
        title: str,
        base_batch: ExtractionBatch,
        llm_batch: ExtractionBatch | None,
    ) -> ExtractionBatch:
        metadata = {**base_batch.metadata, "llm_enrichment_used": llm_batch is not None, "chunking_used": False}
        if llm_batch is not None:
            metadata["llm_notes"] = llm_batch.metadata.get("notes")
            metadata["llm_provider"] = llm_batch.metadata.get("provider")
            metadata["llm_model"] = llm_batch.metadata.get("model")
            metadata["llm_base_url"] = llm_batch.metadata.get("base_url")

        merged_batch = self._merge_batch_collection(
            document_id=document_id,
            title=title,
            batches=[base_batch, llm_batch],
            strategy="schema_rules+llm" if llm_batch is not None else base_batch.strategy,
            metadata=metadata,
        )
        merged_batch.metadata.setdefault("merged_candidate_count", len(merged_batch.candidates))
        merged_batch.metadata.setdefault("merged_relation_count", len(merged_batch.relations))
        return merged_batch

    def _merge_chunk_batches(
        self,
        *,
        document_id: str,
        title: str,
        chunks: list[DocumentChunk],
        chunk_batches: list[ExtractionBatch],
    ) -> ExtractionBatch:
        metadata = {
            "chunking_used": True,
            "chunk_count": len(chunks),
            "chunk_char_limit": settings.formal_chunk_char_limit,
            "chunk_candidate_count_total": sum(len(batch.candidates) for batch in chunk_batches),
            "chunk_relation_count_total": sum(len(batch.relations) for batch in chunk_batches),
            "llm_enrichment_used": any(batch.metadata.get("llm_enrichment_used") for batch in chunk_batches),
            "llm_provider": self._first_metadata_value(chunk_batches, "llm_provider"),
            "llm_model": self._first_metadata_value(chunk_batches, "llm_model"),
            "llm_base_url": self._first_metadata_value(chunk_batches, "llm_base_url"),
        }
        llm_notes = [note for note in (batch.metadata.get("llm_notes") for batch in chunk_batches) if note]
        if llm_notes:
            metadata["llm_notes"] = llm_notes

        merged_batch = self._merge_batch_collection(
            document_id=document_id,
            title=title,
            batches=chunk_batches,
            strategy="chunked_schema_rules+llm",
            metadata=metadata,
        )
        merged_batch.metadata["merged_candidate_count"] = len(merged_batch.candidates)
        merged_batch.metadata["merged_relation_count"] = len(merged_batch.relations)
        return merged_batch

    def _merge_batch_collection(
        self,
        *,
        document_id: str,
        title: str,
        batches: list[ExtractionBatch | None],
        strategy: str,
        metadata: dict,
    ) -> ExtractionBatch:
        merged_candidates: dict[tuple[str, str], ExtractedCandidate] = {}
        merged_relations: dict[tuple[str, str, str], ExtractedRelation] = {}

        for batch in batches:
            if batch is None:
                continue
            for candidate in batch.candidates:
                key = (candidate.item_type, candidate.canonical_name)
                existing = merged_candidates.get(key)
                if existing is None:
                    merged_candidates[key] = candidate.model_copy(
                        deep=True,
                        update={"payload": self._normalize_payload(candidate.payload)},
                    )
                    continue

                merged_candidates[key] = existing.model_copy(
                    update={
                        "confidence": max(existing.confidence, candidate.confidence),
                        "payload": self._merge_payloads(existing.payload, candidate.payload),
                    }
                )

            for relation in batch.relations:
                key = (relation.relation_type, relation.source_name, relation.target_name)
                existing = merged_relations.get(key)
                if existing is None:
                    merged_relations[key] = relation.model_copy(
                        deep=True,
                        update={"payload": self._normalize_payload(relation.payload)},
                    )
                    continue

                merged_relations[key] = existing.model_copy(
                    update={
                        "confidence": max(existing.confidence, relation.confidence),
                        "payload": self._merge_payloads(existing.payload, relation.payload),
                    }
                )

        return ExtractionBatch(
            document_id=document_id,
            title=title,
            strategy=strategy,
            candidates=list(merged_candidates.values()),
            relations=list(merged_relations.values()),
            metadata=metadata,
        )

    def _build_llm_prompt(
        self,
        *,
        title: str,
        file_path: str,
        segments: list[ParsedSegment],
        base_batch: ExtractionBatch,
        scope_label: str | None = None,
        sample_segments: bool = True,
    ) -> str:
        excerpt_segments = self._select_llm_segments(segments) if sample_segments else segments
        excerpt = "\n\n".join(
            f"[{segment.block_type}] {segment.heading}\n{segment.content}"
            for segment in excerpt_segments
        )
        base_summary = {
            "candidates": [
                {
                    "item_type": item.item_type,
                    "canonical_name": item.canonical_name,
                    "category": item.payload.get("category"),
                    "aliases": item.payload.get("aliases", []),
                }
                for item in base_batch.candidates[:32]
            ],
            "relations": [
                {
                    "relation_type": item.relation_type,
                    "source_name": item.source_name,
                    "target_name": item.target_name,
                }
                for item in base_batch.relations[:48]
            ],
        }
        return (
            "你是软件工厂的领域知识抽取器。请基于下面的文档内容，使用严格结构化输出抽取实体(entity)、事件(event)、流程(process)及关系。"
            "只保留文档中明确出现或能从同一段证据直接确认的内容，不要编造。\n"
            "关系类型仅允许：describes、owned_by、part_of、operational_exchange、participates_in_exchange、scoped_by、process_scoped_by。\n"
            "中文优先输出 canonical_name；若原文是英文且没有中文，再保留英文。evidence 请给出一句最能支撑该抽取结果的证据。\n\n"
            f"文档标题：{title}\n"
            f"文件路径：{file_path}\n"
            f"抽取范围：{scope_label or '全文'}\n\n"
            f"规则抽取结果（供校正和补充）：\n{json.dumps(base_summary, ensure_ascii=False, indent=2)}\n\n"
            f"文档片段：\n{excerpt}"
        )

    def _should_use_chunked_formal_extraction(self, segments: list[ParsedSegment]) -> bool:
        if not self.formal_extraction_mode or not segments:
            return False
        total_chars = sum(len(segment.content) for segment in segments)
        return (
            len(segments) >= settings.formal_chunk_segment_threshold
            or total_chars >= settings.formal_chunk_char_threshold
        )

    def _attach_chunk_source(self, batch: ExtractionBatch, *, chunk: DocumentChunk) -> ExtractionBatch:
        source_ref = {
            "chunk_id": chunk.chunk_id,
            "chunk_heading": chunk.heading,
            "segment_ids": chunk.segment_ids,
            "anchors": chunk.anchors,
        }
        return batch.model_copy(
            update={
                "candidates": [
                    candidate.model_copy(
                        update={"payload": self._normalize_payload(candidate.payload, source_ref=source_ref)}
                    )
                    for candidate in batch.candidates
                ],
                "relations": [
                    relation.model_copy(
                        update={"payload": self._normalize_payload(relation.payload, source_ref=source_ref)}
                    )
                    for relation in batch.relations
                ],
            }
        )

    @staticmethod
    def _normalize_payload(payload: dict | None, *, source_ref: dict | None = None) -> dict:
        normalized = dict(payload or {})
        aliases = [alias.strip() for alias in normalized.get("aliases", []) if isinstance(alias, str) and alias.strip()]
        normalized["aliases"] = list(dict.fromkeys(aliases))

        evidence_values = ExtractionService._merge_string_lists(
            [normalized.get("evidence")],
            normalized.get("evidence_list", []) or [],
        )
        if evidence_values:
            normalized["evidence"] = evidence_values[0]
            normalized["evidence_list"] = evidence_values

        source_refs = ExtractionService._merge_source_refs(
            normalized.get("source_refs", []) or [],
            [source_ref] if source_ref else [],
        )
        if source_refs:
            normalized["source_refs"] = source_refs

        return normalized

    @staticmethod
    def _merge_payloads(existing_payload: dict, incoming_payload: dict) -> dict:
        existing_normalized = ExtractionService._normalize_payload(existing_payload)
        incoming_normalized = ExtractionService._normalize_payload(incoming_payload)
        merged_payload = {
            **existing_normalized,
            **{
                key: value
                for key, value in incoming_normalized.items()
                if key not in {"aliases", "evidence", "evidence_list", "source_refs"} and value not in (None, "", [])
            },
        }
        merged_payload["aliases"] = ExtractionService._merge_string_lists(
            existing_normalized.get("aliases", []),
            incoming_normalized.get("aliases", []),
        )
        evidence_list = ExtractionService._merge_string_lists(
            [existing_normalized.get("evidence"), *(existing_normalized.get("evidence_list", []) or [])],
            [incoming_normalized.get("evidence"), *(incoming_normalized.get("evidence_list", []) or [])],
        )
        if evidence_list:
            merged_payload["evidence"] = evidence_list[0]
            merged_payload["evidence_list"] = evidence_list
        merged_source_refs = ExtractionService._merge_source_refs(
            existing_normalized.get("source_refs", []) or [],
            incoming_normalized.get("source_refs", []) or [],
        )
        if merged_source_refs:
            merged_payload["source_refs"] = merged_source_refs
        return merged_payload

    @staticmethod
    def _merge_string_lists(left: list[Any], right: list[Any]) -> list[str]:
        merged: list[str] = []
        for value in [*left, *right]:
            if not isinstance(value, str):
                continue
            normalized = value.strip()
            if normalized and normalized not in merged:
                merged.append(normalized)
        return merged

    @staticmethod
    def _merge_source_refs(left: list[Any], right: list[Any]) -> list[dict]:
        merged: list[dict] = []
        seen: set[str] = set()
        for value in [*left, *right]:
            if not isinstance(value, dict):
                continue
            serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
            if serialized in seen:
                continue
            seen.add(serialized)
            merged.append(value)
        return merged

    @staticmethod
    def _first_metadata_value(batches: list[ExtractionBatch], key: str) -> Any:
        for batch in batches:
            value = batch.metadata.get(key)
            if value not in (None, "", []):
                return value
        return None

    @staticmethod
    def _select_llm_segments(segments: list[ParsedSegment]) -> list[ParsedSegment]:
        if not segments:
            return []

        indexed_segments = list(enumerate(segments))
        limit = settings.llm_enrichment_segment_limit
        window_count = min(limit, len(indexed_segments))

        selected: list[ParsedSegment] = []
        selected_ids: set[int] = set()
        total_chars = 0

        def try_add(segment: ParsedSegment) -> None:
            nonlocal total_chars
            key = id(segment)
            if key in selected_ids:
                return
            candidate_size = len(segment.heading) + len(segment.content)
            if len(selected) >= settings.llm_enrichment_segment_limit:
                return
            if total_chars + candidate_size > settings.llm_enrichment_char_limit:
                return
            selected.append(segment)
            selected_ids.add(key)
            total_chars += candidate_size

        for _, segment in ExtractionService._pick_window_candidates(indexed_segments, window_count):
            try_add(segment)

        remaining = sorted(
            indexed_segments,
            key=lambda item: (
                -ExtractionService._segment_priority(item[1]),
                item[0],
            ),
        )
        for _, segment in remaining:
            try_add(segment)

        selected.sort(key=lambda segment: next(index for index, item in indexed_segments if item is segment))
        return selected

    @staticmethod
    def _pick_window_candidates(
        indexed_segments: list[tuple[int, ParsedSegment]], window_count: int
    ) -> list[tuple[int, ParsedSegment]]:
        if window_count <= 0:
            return []

        candidates: list[tuple[int, ParsedSegment]] = []
        total = len(indexed_segments)
        for slot in range(window_count):
            start = int(slot * total / window_count)
            end = max(start + 1, int((slot + 1) * total / window_count))
            window = indexed_segments[start:end]
            if slot == 0:
                candidates.append(window[0])
                continue
            if slot == window_count - 1:
                candidates.append(window[-1])
                continue
            best = max(
                window,
                key=lambda item: (
                    ExtractionService._segment_priority(item[1]),
                    len(item[1].content),
                    -item[0],
                ),
            )
            candidates.append(best)
        return candidates

    @staticmethod
    def _segment_priority(segment: ParsedSegment) -> int:
        content = segment.content.strip()
        heading = segment.heading.strip()
        score = 0

        if segment.block_type == "table_row":
            score += 4
        elif segment.block_type == "paragraph":
            score += 1

        score += min(len(content) // 180, 4)

        if ExtractionService._looks_relation_dense(content):
            score += 2
        if ExtractionService._looks_low_signal(heading, content):
            score -= 4

        return score

    @staticmethod
    def _looks_relation_dense(content: str) -> bool:
        hints = ("|", "->", "=>", "关系", "流程", "节点", "交换", "输入", "输出", "接口", "I/O")
        return any(hint in content for hint in hints)

    @staticmethod
    def _looks_low_signal(heading: str, content: str) -> bool:
        normalized_heading = heading.strip().lower()
        normalized_content = content.strip().lower()
        if len(content.strip()) < 24:
            return True
        if normalized_heading in {"contents", "page", "table of contents"}:
            return True
        if "distribution restriction" in normalized_content and len(content) < 200:
            return True

        tokens = re.findall(r"\S+", content)
        single_letter_tokens = re.findall(r"\b[A-Za-z]\b", content)
        if tokens and len(single_letter_tokens) / len(tokens) > 0.45:
            return True
        return False
