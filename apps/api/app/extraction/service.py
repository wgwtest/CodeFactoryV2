import json
import re
from pathlib import Path

from app.config import settings
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
        source_document = SourceDocument(
            path=file_path,
            title=title,
            file_type=Path(file_path).suffix.lstrip(".") or "txt",
            source_archive="runtime",
            text="\n".join(segment.content for segment in segments),
        )
        base_batch = extract_document_batch(document_id=document_id, document=source_document, segments=segments)
        llm_batch = self._try_llm_enrichment(
            document_id=document_id,
            title=title,
            file_path=file_path,
            segments=segments,
            base_batch=base_batch,
        )
        return self._merge_batches(document_id=document_id, title=title, base_batch=base_batch, llm_batch=llm_batch)

    def _try_llm_enrichment(
        self,
        *,
        document_id: str,
        title: str,
        file_path: str,
        segments: list[ParsedSegment],
        base_batch: ExtractionBatch,
    ) -> ExtractionBatch | None:
        del document_id
        if not (self.formal_extraction_mode or settings.llm_enrichment_enabled):
            return None

        prompt = self._build_llm_prompt(title=title, file_path=file_path, segments=segments, base_batch=base_batch)

        try:
            structured_llm, llm_metadata = build_structured_llm(output_schema=StructuredExtractionResponse)
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
                    payload={
                        "category": item.category,
                        "aliases": [alias.strip() for alias in item.aliases if alias.strip()],
                        "evidence": item.evidence,
                    },
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
                    payload={"evidence": relation.evidence},
                )
                for relation in result.relations
                if relation.source_name.strip() and relation.target_name.strip()
            ],
            metadata={**llm_metadata, "notes": result.notes},
        )

    def _merge_batches(
        self,
        *,
        document_id: str,
        title: str,
        base_batch: ExtractionBatch,
        llm_batch: ExtractionBatch | None,
    ) -> ExtractionBatch:
        merged_candidates: dict[tuple[str, str], ExtractedCandidate] = {}
        merged_relations: dict[tuple[str, str, str], ExtractedRelation] = {}

        for batch in [base_batch, llm_batch]:
            if batch is None:
                continue
            for candidate in batch.candidates:
                key = (candidate.item_type, candidate.canonical_name)
                existing = merged_candidates.get(key)
                if existing is None:
                    merged_candidates[key] = candidate.model_copy(deep=True)
                    continue

                merged_payload = {
                    **existing.payload,
                    **{key: value for key, value in candidate.payload.items() if value not in (None, "", [])},
                }
                aliases = [
                    alias
                    for alias in [*existing.payload.get("aliases", []), *candidate.payload.get("aliases", [])]
                    if alias
                ]
                if aliases:
                    merged_payload["aliases"] = list(dict.fromkeys(aliases))
                if candidate.payload.get("evidence") and not existing.payload.get("evidence"):
                    merged_payload["evidence"] = candidate.payload["evidence"]

                merged_candidates[key] = existing.model_copy(
                    update={
                        "confidence": max(existing.confidence, candidate.confidence),
                        "payload": merged_payload,
                    }
                )

            for relation in batch.relations:
                key = (relation.relation_type, relation.source_name, relation.target_name)
                existing = merged_relations.get(key)
                if existing is None:
                    merged_relations[key] = relation.model_copy(deep=True)
                    continue

                merged_payload = {
                    **existing.payload,
                    **{key: value for key, value in relation.payload.items() if value not in (None, "", [])},
                }
                merged_relations[key] = existing.model_copy(
                    update={
                        "confidence": max(existing.confidence, relation.confidence),
                        "payload": merged_payload,
                    }
                )

        metadata = {**base_batch.metadata, "llm_enrichment_used": llm_batch is not None}
        if llm_batch is not None:
            metadata["llm_notes"] = llm_batch.metadata.get("notes")
            metadata["llm_provider"] = llm_batch.metadata.get("provider")
            metadata["llm_model"] = llm_batch.metadata.get("model")
            metadata["llm_base_url"] = llm_batch.metadata.get("base_url")

        return ExtractionBatch(
            document_id=document_id,
            title=title,
            strategy="schema_rules+llm" if llm_batch is not None else base_batch.strategy,
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
    ) -> str:
        excerpt_segments = self._select_llm_segments(segments)
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
            f"文件路径：{file_path}\n\n"
            f"规则抽取结果（供校正和补充）：\n{json.dumps(base_summary, ensure_ascii=False, indent=2)}\n\n"
            f"文档片段：\n{excerpt}"
        )

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
