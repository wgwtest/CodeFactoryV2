import json
import re
from pathlib import Path
from typing import Any, Callable

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
    def __init__(
        self,
        *,
        formal_extraction_mode: bool = False,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.formal_extraction_mode = formal_extraction_mode
        self.progress_callback = progress_callback

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
        unified_trace = self._build_unified_document_stage_trace(
            document_id=document_id,
            title=title,
            file_path=file_path,
            segments=segments,
            source_document=source_document,
        )
        self._emit_stage_event(
            stage_id="unified_document_object",
            stage_label="Unified Document Object",
            status="completed" if segments else "warning",
            message=(
                f"Unified document object normalized {len(segments)} parsed segments."
                if segments
                else "Unified document object could not be materialized because no parsed segments were available."
            ),
            runtime_trace=unified_trace,
        )
        if self._should_use_chunked_formal_extraction(segments):
            batch = self._extract_with_chunks(
                document_id=document_id,
                title=title,
                file_path=file_path,
                segments=segments,
                source_document=source_document,
                unified_trace=unified_trace,
            )
        else:
            batch = self._extract_standard_document(
                document_id=document_id,
                title=title,
                file_path=file_path,
                segments=segments,
                source_document=source_document,
                unified_trace=unified_trace,
            )
        batch.metadata["runtime_trace"] = {
            **dict(batch.metadata.get("runtime_trace") or {}),
            "unified_document_object": unified_trace,
        }
        return batch

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
            segment_count=len(segments),
            segments=segments,
        )

    def _extract_standard_document(
        self,
        *,
        document_id: str,
        title: str,
        file_path: str,
        segments: list[ParsedSegment],
        source_document: SourceDocument,
        unified_trace: dict[str, Any],
    ) -> ExtractionBatch:
        self._emit_stage_event(
            stage_id="evidence_constructor",
            stage_label="Evidence Constructor",
            status="running",
            message="Unified document content is being converted into traceable evidence units.",
            runtime_trace=self._build_evidence_constructor_stage_trace(
                document_id=document_id,
                title=title,
                source_document=source_document,
                batches=[],
            ),
        )
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
        merged_batch = self._merge_standard_batches(
            document_id=document_id,
            title=title,
            base_batch=base_batch,
            llm_batch=llm_batch,
        )
        evidence_trace = self._build_evidence_constructor_stage_trace(
            document_id=document_id,
            title=title,
            source_document=source_document,
            batches=[merged_batch],
        )
        chunk_trace = self._build_chunk_layer_stage_trace(
            document_id=document_id,
            title=title,
            source_document=source_document,
            chunk_batches=[merged_batch],
        )
        merged_batch.metadata["runtime_trace"] = {
            "unified_document_object": unified_trace,
            "evidence_constructor": evidence_trace,
            "evidence_graph_chunk_layer": chunk_trace,
        }
        self._emit_stage_event(
            stage_id="evidence_constructor",
            stage_label="Evidence Constructor",
            status="completed" if merged_batch.candidates else "warning",
            message=f"Evidence constructor produced {len(evidence_trace.get('evidence_units', []))} evidence units.",
            runtime_trace=evidence_trace,
        )
        self._emit_stage_event(
            stage_id="evidence_graph_chunk_layer",
            stage_label="Evidence Graph / Chunk Layer",
            status="completed" if chunk_trace.get("chunks") else "warning",
            message=f"Chunk layer assembled {len(chunk_trace.get('chunks', []))} chunk windows.",
            runtime_trace=chunk_trace,
        )
        return merged_batch

    def _extract_with_chunks(
        self,
        *,
        document_id: str,
        title: str,
        file_path: str,
        segments: list[ParsedSegment],
        source_document: SourceDocument,
        unified_trace: dict[str, Any],
    ) -> ExtractionBatch:
        chunks = build_document_chunks(segments, max_chars=settings.formal_chunk_char_limit)
        structured_llm_bundle = self._build_structured_llm_bundle()
        resolved_chunk_batches: list[tuple[DocumentChunk, ExtractionBatch]] = []
        chunk_total = len(chunks)
        self._emit_stage_event(
            stage_id="evidence_constructor",
            stage_label="Evidence Constructor",
            status="running",
            message="Unified document content is being converted into traceable evidence units.",
            runtime_trace=self._build_evidence_constructor_stage_trace(
                document_id=document_id,
                title=title,
                source_document=source_document,
                batches=[],
            ),
        )
        self._emit_stage_event(
            stage_id="evidence_graph_chunk_layer",
            stage_label="Evidence Graph / Chunk Layer",
            status="running",
            message=f"Chunk planner prepared {chunk_total} chunk windows for staged evidence processing.",
            runtime_trace=self._build_chunk_layer_stage_trace(
                document_id=document_id,
                title=title,
                source_document=source_document,
                chunk_batches=[],
                planned_chunks=chunks,
            ),
        )
        for chunk_position, chunk in enumerate(chunks, start=1):
            resolved_chunk_batches.extend(
                self._extract_chunk_batch_with_retry(
                    document_id=document_id,
                    title=title,
                    file_path=file_path,
                    source_document=source_document,
                    chunk=chunk,
                    structured_llm_bundle=structured_llm_bundle,
                    chunk_position=chunk_position,
                    chunk_total=chunk_total,
                )
            )
            processed_batches = [batch for _chunk, batch in resolved_chunk_batches]
            self._emit_stage_event(
                stage_id="evidence_constructor",
                stage_label="Evidence Constructor",
                status="running",
                message=(
                    f"Evidence constructor has processed {len(processed_batches)} chunk outputs and "
                    f"assembled {sum(len(batch.candidates) for batch in processed_batches)} evidence candidates."
                ),
                runtime_trace=self._build_evidence_constructor_stage_trace(
                    document_id=document_id,
                    title=title,
                    source_document=source_document,
                    batches=processed_batches,
                ),
            )
            self._emit_stage_event(
                stage_id="evidence_graph_chunk_layer",
                stage_label="Evidence Graph / Chunk Layer",
                status="running",
                message=f"Chunk graph has materialized {len(processed_batches)} resolved chunk windows so far.",
                runtime_trace=self._build_chunk_layer_stage_trace(
                    document_id=document_id,
                    title=title,
                    source_document=source_document,
                    chunk_batches=processed_batches,
                    planned_chunks=chunks,
                ),
            )
        merged_batch = self._merge_chunk_batches(
            document_id=document_id,
            title=title,
            chunks=[chunk for chunk, _batch in resolved_chunk_batches],
            chunk_batches=[batch for _chunk, batch in resolved_chunk_batches],
        )
        evidence_trace = self._build_evidence_constructor_stage_trace(
            document_id=document_id,
            title=title,
            source_document=source_document,
            batches=[batch for _chunk, batch in resolved_chunk_batches],
        )
        chunk_trace = self._build_chunk_layer_stage_trace(
            document_id=document_id,
            title=title,
            source_document=source_document,
            chunk_batches=[batch for _chunk, batch in resolved_chunk_batches],
            planned_chunks=[chunk for chunk, _batch in resolved_chunk_batches],
        )
        merged_batch.metadata["runtime_trace"] = {
            "unified_document_object": unified_trace,
            "evidence_constructor": evidence_trace,
            "evidence_graph_chunk_layer": chunk_trace,
        }
        self._emit_stage_event(
            stage_id="evidence_constructor",
            stage_label="Evidence Constructor",
            status="completed" if evidence_trace.get("evidence_units") else "warning",
            message=f"Evidence constructor produced {len(evidence_trace.get('evidence_units', []))} evidence units.",
            runtime_trace=evidence_trace,
        )
        self._emit_stage_event(
            stage_id="evidence_graph_chunk_layer",
            stage_label="Evidence Graph / Chunk Layer",
            status="completed" if chunk_trace.get("chunks") else "warning",
            message=f"Chunk layer assembled {len(chunk_trace.get('chunks', []))} chunk windows.",
            runtime_trace=chunk_trace,
        )
        return merged_batch

    def _extract_chunk_batch_with_retry(
        self,
        *,
        document_id: str,
        title: str,
        file_path: str,
        source_document: SourceDocument,
        chunk: DocumentChunk,
        structured_llm_bundle: tuple[Any, dict[str, str | None]] | None,
        chunk_position: int,
        chunk_total: int,
        retry_depth: int = 0,
    ) -> list[tuple[DocumentChunk, ExtractionBatch]]:
        self._emit_chunk_progress(
            chunk=chunk,
            chunk_position=chunk_position,
            chunk_total=chunk_total,
            retry_depth=retry_depth,
        )
        try:
            batch = self._extract_chunk_batch(
                document_id=document_id,
                title=title,
                file_path=file_path,
                source_document=source_document,
                chunk=chunk,
                structured_llm_bundle=structured_llm_bundle,
            )
            return [(chunk, batch)]
        except ValueError as exc:
            if not self._should_retry_chunk_split(exc=exc, chunk=chunk, retry_depth=retry_depth):
                raise

            retried_chunks = self._build_retry_chunks(chunk, retry_depth=retry_depth)
            resolved_batches: list[tuple[DocumentChunk, ExtractionBatch]] = []
            for retried_chunk in retried_chunks:
                resolved_batches.extend(
                    self._extract_chunk_batch_with_retry(
                        document_id=document_id,
                        title=title,
                        file_path=file_path,
                        source_document=source_document,
                        chunk=retried_chunk,
                        structured_llm_bundle=structured_llm_bundle,
                        chunk_position=chunk_position,
                        chunk_total=chunk_total,
                        retry_depth=retry_depth + 1,
                    )
                )
            return resolved_batches

    def _emit_chunk_progress(
        self,
        *,
        chunk: DocumentChunk,
        chunk_position: int,
        chunk_total: int,
        retry_depth: int,
    ) -> None:
        if self.progress_callback is None:
            return
        self.progress_callback(
            {
                "event": "chunk_progress",
                "chunk_id": chunk.chunk_id,
                "chunk_position": chunk_position,
                "chunk_total": chunk_total,
                "chunk_heading": chunk.heading,
                "chunk_char_count": chunk.char_count,
                "chunk_segment_count": len(chunk.segments),
                "retry_depth": retry_depth,
            }
        )

    def _should_retry_chunk_split(self, *, exc: ValueError, chunk: DocumentChunk, retry_depth: int) -> bool:
        if not self.formal_extraction_mode:
            return False
        if retry_depth >= 6:
            return False

        error_message = str(exc)
        retryable_markers = (
            "Invalid JSON",
            "json_invalid",
            "EOF while parsing",
            "schema 校验",
            "响应无法通过 schema 校验",
            "Request timed out",
            "ReadTimeout",
        )
        if not any(marker in error_message for marker in retryable_markers):
            return False

        return chunk.char_count > 80

    def _build_retry_chunks(self, chunk: DocumentChunk, *, retry_depth: int) -> list[DocumentChunk]:
        next_max_chars = max(80, chunk.char_count // 2)
        if next_max_chars >= chunk.char_count:
            raise ValueError("正式知识库抽取失败：无法继续缩小问题块，结构化大模型输出仍不可解析")

        retry_chunks = build_document_chunks(chunk.segments, max_chars=next_max_chars)
        if len(retry_chunks) <= 1 and retry_chunks[0].char_count >= chunk.char_count:
            raise ValueError("正式知识库抽取失败：问题块无法被进一步细分，结构化大模型输出仍不可解析")

        namespaced_chunks: list[DocumentChunk] = []
        for retry_chunk in retry_chunks:
            namespaced_chunks.append(
                DocumentChunk(
                    chunk_id=f"{chunk.chunk_id}.r{retry_depth + 1}-{retry_chunk.chunk_index + 1:03d}",
                    chunk_index=retry_chunk.chunk_index,
                    heading=retry_chunk.heading,
                    segments=retry_chunk.segments,
                    segment_ids=retry_chunk.segment_ids,
                    char_count=retry_chunk.char_count,
                    block_types=retry_chunk.block_types,
                    anchors=retry_chunk.anchors,
                )
            )
        return namespaced_chunks

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
            "LLM 只负责对规则抽取结果做校正、高价值补充和去重，不要机械重复规则结果已经覆盖的大量条目。\n"
            "如果当前片段是术语表、符号表、条目清单或大表格，不要逐项穷举整个表，只提取上层分类、关键概念、关键对象和最重要关系。\n"
            "candidates 最多返回 24 条，relations 最多返回 16 条；优先返回跨段可复用、对建模有价值的内容。\n\n"
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

    def _emit_stage_event(
        self,
        *,
        stage_id: str,
        stage_label: str,
        status: str,
        message: str,
        runtime_trace: dict[str, Any] | None = None,
    ) -> None:
        if self.progress_callback is None:
            return
        self.progress_callback(
            {
                "event": "stage_transition",
                "stage_id": stage_id,
                "stage_label": stage_label,
                "status": status,
                "message": message,
                "runtime_trace": runtime_trace,
            }
        )

    def _build_unified_document_stage_trace(
        self,
        *,
        document_id: str,
        title: str,
        file_path: str,
        segments: list[ParsedSegment],
        source_document: SourceDocument,
    ) -> dict[str, Any]:
        section_labels = [segment.heading.strip() for segment in segments if segment.heading.strip()]
        normalized_sections = list(dict.fromkeys(section_labels))
        return {
            "input_count": len(segments),
            "output_count": len(segments),
            "decision_summary": "normalize parser segments into a stable unified document object",
            "ai_summary": "field alignment and heading normalization are applied before downstream evidence stages",
            "events": [
                self._trace_event(
                    event_id=f"{document_id}:unified:normalized",
                    kind="result",
                    level="success" if segments else "warning",
                    message=(
                        f"Unified document object normalized {len(segments)} parsed segments from {file_path}."
                        if segments
                        else f"Unified document object could not normalize any parsed segments from {file_path}."
                    ),
                    object_id=f"{document_id}:unified-document",
                    object_kind="node",
                )
            ],
            "sections": [
                self._trace_section(
                    section_id="trace-unified-summary",
                    title="Runtime Trace",
                    fields=[
                        self._trace_field("document_title", "document_title", title),
                        self._trace_field("input_count", "input_count", str(len(segments))),
                        self._trace_field("output_count", "output_count", str(len(segments))),
                        self._trace_field("section_count", "section_count", str(len(normalized_sections))),
                        self._trace_field("parser_name", "parser_name", source_document.parser_name or "unknown"),
                    ],
                )
            ],
        }

    def _build_evidence_constructor_stage_trace(
        self,
        *,
        document_id: str,
        title: str,
        source_document: SourceDocument,
        batches: list[ExtractionBatch],
    ) -> dict[str, Any]:
        evidence_units: list[dict[str, Any]] = []
        anchor_labels: set[str] = set()
        for batch in batches:
            for candidate in batch.candidates:
                payload = dict(candidate.payload or {})
                source_refs = list(payload.get("source_refs") or [])
                anchor_label = self._extract_anchor_label(source_refs)
                if anchor_label:
                    anchor_labels.add(anchor_label)
                evidence_units.append(
                    {
                        "unit_id": f"{candidate.item_type}:{candidate.canonical_name}:{len(evidence_units) + 1}",
                        "source_item_id": payload.get("id") or f"{candidate.item_type}:{candidate.canonical_name}",
                        "source_item_name": candidate.canonical_name,
                        "source_kind": candidate.item_type,
                        "excerpt": payload.get("evidence") or "",
                        "anchor_label": anchor_label or "unanchored",
                        "source_refs": source_refs,
                    }
                )
        llm_notes = [batch.metadata.get("llm_notes") for batch in batches if batch.metadata.get("llm_notes")]
        rule_hits = [
            {
                "key": "anchor_present",
                "label": "anchor_present",
                "detail": f"{sum(1 for unit in evidence_units if unit['anchor_label'] != 'unanchored')} of {len(evidence_units)} evidence units retained source anchors",
            },
            {
                "key": "context_window",
                "label": "context_window",
                "detail": f"constructor used {len(source_document.segments or [])} unified segments as upstream context",
            },
        ]
        return {
            "input_count": len(source_document.segments or []),
            "output_count": len(evidence_units),
            "decision_summary": "convert unified document paragraphs into traceable evidence units",
            "ai_summary": llm_notes[0] if llm_notes else "no llm refinement note recorded",
            "rule_hits": rule_hits,
            "evidence_units": evidence_units,
            "events": [
                self._trace_event(
                    event_id=f"{document_id}:evidence-constructor:trace",
                    kind="result",
                    level="success" if evidence_units else "warning",
                    message=(
                        f"Evidence constructor produced {len(evidence_units)} evidence units for {title}."
                        if evidence_units
                        else f"Evidence constructor has not emitted any evidence units for {title} yet."
                    ),
                    object_id=f"{document_id}:evidence-constructor:units",
                    object_kind="node",
                )
            ],
            "sections": [
                self._trace_section(
                    section_id="trace-evidence-constructor",
                    title="Runtime Trace",
                    fields=[
                        self._trace_field("input_count", "input_count", str(len(source_document.segments or []))),
                        self._trace_field("output_count", "output_count", str(len(evidence_units))),
                        self._trace_field("anchor_count", "anchor_count", str(len(anchor_labels))),
                        self._trace_field("rule_hit_count", "rule_hit_count", str(len(rule_hits))),
                        self._trace_field("ai_summary", "ai_summary", llm_notes[0] if llm_notes else "none"),
                    ],
                )
            ],
        }

    def _build_chunk_layer_stage_trace(
        self,
        *,
        document_id: str,
        title: str,
        source_document: SourceDocument,
        chunk_batches: list[ExtractionBatch],
        planned_chunks: list[DocumentChunk] | None = None,
    ) -> dict[str, Any]:
        chunks: list[dict[str, Any]] = []
        for batch in chunk_batches:
            chunk_id = str(batch.metadata.get("chunk_id") or f"chunk-{len(chunks) + 1}")
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "chunk_label": str(batch.metadata.get("chunk_heading") or chunk_id),
                    "chunk_index": int(batch.metadata.get("chunk_index") or len(chunks)),
                    "chunk_position": len(chunks) + 1,
                    "chunk_total": len(chunk_batches),
                    "chunk_heading": batch.metadata.get("chunk_heading"),
                    "chunk_char_count": int(batch.metadata.get("chunk_char_count") or 0),
                    "chunk_segment_count": int(batch.metadata.get("chunk_segment_count") or 0),
                    "retry_depth": int(batch.metadata.get("retry_depth") or 0),
                    "boundary_adjusted": int(batch.metadata.get("retry_depth") or 0) > 0,
                    "source_refs": self._collect_batch_source_refs(batch),
                    "evidence_unit_count": len(batch.candidates),
                }
            )
        if not chunks and planned_chunks:
            for index, chunk in enumerate(planned_chunks, start=1):
                chunks.append(
                    {
                        "chunk_id": chunk.chunk_id,
                        "chunk_label": chunk.heading or f"Chunk {index}",
                        "chunk_index": chunk.chunk_index,
                        "chunk_position": index,
                        "chunk_total": len(planned_chunks),
                        "chunk_heading": chunk.heading,
                        "chunk_char_count": chunk.char_count,
                        "chunk_segment_count": len(chunk.segments),
                        "retry_depth": 0,
                        "boundary_adjusted": False,
                        "source_refs": [
                            {
                                "chunk_id": chunk.chunk_id,
                                "chunk_heading": chunk.heading,
                                "segment_ids": chunk.segment_ids,
                                "anchors": chunk.anchors,
                            }
                        ],
                        "evidence_unit_count": 0,
                    }
                )
        adjusted_count = sum(1 for chunk in chunks if chunk.get("boundary_adjusted"))
        planned_count = len(planned_chunks or chunks)
        return {
            "input_count": len(source_document.segments or []),
            "output_count": len(chunks),
            "decision_summary": "group evidence units into chunk windows and connect them as a stage-local graph layer",
            "ai_summary": f"planned {planned_count} chunk windows with {adjusted_count} boundary adjustments",
            "chunks": chunks,
            "events": [
                self._trace_event(
                    event_id=f"{document_id}:chunk-layer:trace",
                    kind="progress" if chunk_batches else "info",
                    level="info" if chunks else "warning",
                    message=(
                        f"Chunk layer currently tracks {len(chunks)} chunk windows for {title}."
                        if chunks
                        else f"Chunk layer has not materialized any chunk windows for {title} yet."
                    ),
                    object_id=f"{document_id}:chunk-group",
                    object_kind="node",
                )
            ],
            "sections": [
                self._trace_section(
                    section_id="trace-chunk-layer",
                    title="Runtime Trace",
                    fields=[
                        self._trace_field("input_count", "input_count", str(len(source_document.segments or []))),
                        self._trace_field("output_count", "output_count", str(len(chunks))),
                        self._trace_field("planned_chunk_count", "planned_chunk_count", str(planned_count)),
                        self._trace_field("boundary_adjusted_count", "boundary_adjusted_count", str(adjusted_count)),
                    ],
                )
            ],
        }

    @staticmethod
    def _collect_batch_source_refs(batch: ExtractionBatch) -> list[dict[str, Any]]:
        source_refs: list[dict[str, Any]] = []
        for candidate in batch.candidates:
            for source_ref in candidate.payload.get("source_refs", []) or []:
                if source_ref not in source_refs:
                    source_refs.append(source_ref)
        return source_refs

    @staticmethod
    def _extract_anchor_label(source_refs: list[dict[str, Any]]) -> str | None:
        for source_ref in source_refs:
            for anchor in source_ref.get("anchors", []) or []:
                page = anchor.get("page")
                paragraph = anchor.get("paragraph")
                block = anchor.get("block")
                parts = []
                if page is not None:
                    parts.append(f"p.{page}")
                if paragraph is not None:
                    parts.append(f"para.{paragraph}")
                if block is not None:
                    parts.append(f"block.{block}")
                if parts:
                    return " / ".join(parts)
        return None

    @staticmethod
    def _trace_event(
        event_id: str,
        kind: str,
        level: str,
        message: str,
        object_id: str | None = None,
        object_kind: str | None = None,
    ) -> dict[str, Any]:
        return {
            "event_id": event_id,
            "kind": kind,
            "level": level,
            "message": message,
            "object_id": object_id,
            "object_kind": object_kind,
        }

    @staticmethod
    def _trace_field(key: str, label: str, value: str, tone: str = "neutral") -> dict[str, str]:
        return {
            "key": key,
            "label": label,
            "value": value,
            "tone": tone,
        }

    @staticmethod
    def _trace_section(section_id: str, title: str, fields: list[dict[str, str]]) -> dict[str, Any]:
        return {
            "section_id": section_id,
            "title": title,
            "fields": fields,
        }

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
