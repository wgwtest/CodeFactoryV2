from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class WorkingDocumentUpdateResult:
    working_document: dict
    applied_block_ids: list[str]
    applied_fragment_ids: list[str]
    blocks: list[dict]
    before_excerpt: str
    after_excerpt: str

    def to_dict(self) -> dict:
        return {
            "applied_block_ids": self.applied_block_ids,
            "applied_fragment_ids": self.applied_fragment_ids,
            "blocks": self.blocks,
            "before_excerpt": self.before_excerpt,
            "after_excerpt": self.after_excerpt,
        }


@dataclass(frozen=True)
class PatchTextResult:
    new_text: str
    start_offset: int
    end_offset: int
    deleted_text: str = ""


class WorkingDocumentService:
    def initialize(self, *, topic: str, template_id: str) -> dict:
        return {
            "document_id": "lab-working-document",
            "title": f"{template_id}需求规格说明（Lab 临时正文）",
            "template_id": template_id,
            "topic": topic,
            "blocks": [],
            "revision_fragments": [],
        }

    def apply_patches(
        self,
        *,
        working_document: dict,
        document_patch: list[dict],
        patch_proposals: list[dict],
        projection_spec_node: dict,
        turn_id: str,
        user_input_summary: str = "",
        target_anchor_plan: list[dict] | None = None,
    ) -> WorkingDocumentUpdateResult:
        self._ensure_shape(working_document)
        before_excerpt = self.render_excerpt(working_document=working_document)
        applied_block_ids: list[str] = []
        applied_fragment_ids: list[str] = []
        changed_blocks: list[dict] = []
        plan_by_id = {
            str(plan.get("plan_id") or "").strip(): dict(plan)
            for plan in list(target_anchor_plan or [])
            if isinstance(plan, dict) and str(plan.get("plan_id") or "").strip()
        }

        for patch in document_patch:
            content = str(patch.get("content") or "").strip()
            if not content:
                continue
            anchor_plan = dict(plan_by_id.get(str(patch.get("plan_ref") or "").strip()) or {})
            anchor_path = self._anchor_path(
                patch=patch,
                projection_spec_node=projection_spec_node,
                anchor_plan=anchor_plan,
            )
            block = self._find_or_create_block(
                working_document=working_document,
                anchor_path=anchor_path,
                display_heading=str(anchor_plan.get("display_heading") or ""),
                plan_ref=str(patch.get("plan_ref") or ""),
            )
            previous_text = str(block.get("text") or "")
            patch_result = self._apply_patch_text(previous_text=previous_text, patch=patch, content=content)
            new_text = patch_result.new_text
            if new_text == previous_text:
                continue

            fragment_id = f"frag-{len(working_document['revision_fragments']) + 1:04d}"
            block["text"] = new_text
            block["last_turn_id"] = turn_id
            if patch.get("plan_ref"):
                block["plan_ref"] = str(patch.get("plan_ref"))
            block["source_fragment_ids"] = self._append_unique(
                list(block.get("source_fragment_ids", [])),
                [fragment_id],
            )
            fragment = {
                "fragment_id": fragment_id,
                "turn_id": turn_id,
                "color_token": self._turn_color_token(turn_id),
                "target_block_id": block["block_id"],
                "apply_mode": str(patch.get("operation") or "append_to_block"),
                "start_offset": patch_result.start_offset,
                "end_offset": patch_result.end_offset,
                "user_input_summary": user_input_summary,
                "supplement_reason": str(patch.get("reason") or "根据本轮输入补入需求规格正文。"),
                "hit_spec_nodes": self._hit_spec_nodes(
                    patch=patch,
                    projection_spec_node=projection_spec_node,
                    anchor_plan=anchor_plan,
                ),
                "source_patch_ids": self._current_patch_ids(
                    patch_proposals=patch_proposals,
                    anchor_path=anchor_path,
                    turn_id=turn_id,
                ),
            }
            if patch_result.deleted_text:
                fragment["deleted_text"] = patch_result.deleted_text
            working_document["revision_fragments"].append(fragment)
            applied_block_ids.append(str(block["block_id"]))
            applied_fragment_ids.append(fragment_id)
            changed_blocks.append(dict(block))

        after_excerpt = self.render_excerpt(working_document=working_document)
        return WorkingDocumentUpdateResult(
            working_document=working_document,
            applied_block_ids=applied_block_ids,
            applied_fragment_ids=applied_fragment_ids,
            blocks=changed_blocks,
            before_excerpt=before_excerpt,
            after_excerpt=after_excerpt,
        )

    def build_review_target(self, *, working_document: dict, anchor_paths: list[str]) -> dict:
        self._ensure_shape(working_document)
        paths = [path for path in anchor_paths if path]
        blocks = [
            block
            for block in working_document["blocks"]
            if not paths or str(block.get("anchor_path") or "") in paths
        ]
        return {
            "review_target_paths": paths,
            "blocks": [dict(block) for block in blocks],
            "excerpt": "\n".join(str(block.get("text") or "").strip() for block in blocks if str(block.get("text") or "").strip()),
        }

    def get_block_snapshot(self, *, working_document: dict, block_id: str) -> dict:
        self._ensure_shape(working_document)
        for block in working_document["blocks"]:
            if str(block.get("block_id") or "") == block_id:
                return dict(block)
        return {
            "block_id": block_id,
            "anchor_path": "",
            "block_type": "paragraph",
            "text": "",
            "last_turn_id": None,
            "source_fragment_ids": [],
        }

    def render_excerpt(self, *, working_document: dict, anchor_paths: list[str] | None = None) -> str:
        self._ensure_shape(working_document)
        paths = set(anchor_paths or [])
        lines: list[str] = []
        for block in working_document["blocks"]:
            if paths and str(block.get("anchor_path") or "") not in paths:
                continue
            text = str(block.get("text") or "").strip()
            if not text:
                continue
            anchor = str(block.get("display_heading") or block.get("anchor_path") or "").strip()
            lines.append(f"{anchor}\n{text}" if anchor else text)
        return "\n\n".join(lines)

    def _ensure_shape(self, working_document: dict) -> None:
        if "blocks" not in working_document:
            blocks = []
            for index, section in enumerate(list(working_document.get("sections", [])), start=1):
                content = str(section.get("content") or "").strip()
                if not content:
                    continue
                anchor_path = str(section.get("target_section") or section.get("section_id") or "")
                blocks.append(
                    self._document_block(
                        block_id=f"blk-{index:04d}",
                        anchor_path=anchor_path,
                        text=content,
                        last_turn_id=section.get("last_turn_id"),
                    )
                )
            working_document["blocks"] = blocks
        working_document.pop("sections", None)
        working_document.setdefault("revision_fragments", [])
        for block in working_document["blocks"]:
            anchor_path = str(block.get("anchor_path") or "")
            block["order_index"] = self._anchor_order_index(anchor_path)
            block["display_heading"] = str(block.get("display_heading") or self._anchor_display_heading(anchor_path))
        working_document["blocks"].sort(key=lambda block: (int(block.get("order_index") or 99_999), str(block.get("block_id") or "")))

    def _find_or_create_block(
        self,
        *,
        working_document: dict,
        anchor_path: str,
        display_heading: str = "",
        plan_ref: str = "",
    ) -> dict:
        for block in working_document["blocks"]:
            if str(block.get("anchor_path") or "") == anchor_path:
                if display_heading:
                    block["display_heading"] = display_heading
                if plan_ref:
                    block["plan_ref"] = plan_ref
                return block
        block = self._document_block(
            block_id=f"blk-{len(working_document['blocks']) + 1:04d}",
            anchor_path=anchor_path,
            display_heading=display_heading or self._anchor_display_heading(anchor_path),
            plan_ref=plan_ref,
        )
        working_document["blocks"].append(block)
        working_document["blocks"].sort(key=lambda item: (int(item.get("order_index") or 99_999), str(item.get("block_id") or "")))
        return block

    @classmethod
    def _document_block(
        cls,
        *,
        block_id: str,
        anchor_path: str,
        text: str = "",
        last_turn_id: str | None = None,
        display_heading: str = "",
        plan_ref: str = "",
    ) -> dict:
        return {
            "block_id": block_id,
            "anchor_path": anchor_path,
            "block_type": "paragraph",
            "order_index": cls._anchor_order_index(anchor_path),
            "display_heading": display_heading or cls._anchor_display_heading(anchor_path),
            "text": text,
            "last_turn_id": last_turn_id,
            "plan_ref": plan_ref,
            "source_fragment_ids": [],
        }

    @classmethod
    def _anchor_order_index(cls, anchor_path: str) -> int:
        section_number, clause_number, _clause_title = cls._parse_anchor_path(anchor_path)
        if section_number <= 0:
            return 99_000
        return section_number * 100 + clause_number * 10

    @classmethod
    def _anchor_display_heading(cls, anchor_path: str) -> str:
        section_number, clause_number, clause_title = cls._parse_anchor_path(anchor_path)
        if section_number > 0 and clause_number > 0 and clause_title:
            return f"{section_number}.{clause_number} {clause_title}"
        return anchor_path.strip()

    @staticmethod
    def _parse_anchor_path(anchor_path: str) -> tuple[int, int, str]:
        normalized = " ".join(str(anchor_path or "").replace("\\", "/").split())
        req_match = re.match(r"^REQ-(?P<section>\d+)\.(?P<clause>\d+)$", normalized)
        if req_match:
            return int(req_match.group("section")), int(req_match.group("clause")), ""
        parts = [part.strip() for part in normalized.split("/") if part.strip()]
        if not parts:
            return 0, 0, ""

        first_part = parts[0]
        first_match = re.match(r"^(?P<section>\d+)(?:\.(?P<clause>\d+))?\s*(?P<title>.*)$", first_part)
        section_number = int(first_match.group("section")) if first_match else 0
        clause_number = int(first_match.group("clause")) if first_match and first_match.group("clause") else 0
        clause_title = first_match.group("title").strip() if first_match and first_match.group("clause") else ""

        if len(parts) > 1:
            clause_title = parts[-1]
            if clause_number <= 0:
                clause_number = WorkingDocumentService._infer_clause_number(
                    section_number=section_number,
                    clause_title=clause_title,
                )
        elif section_number > 0 and clause_number > 0 and not clause_title:
            clause_title = first_part

        return section_number, clause_number, clause_title

    @staticmethod
    def _infer_clause_number(*, section_number: int, clause_title: str) -> int:
        normalized = clause_title.strip()
        clause_orders = {
            1: ["编写目的", "适用范围", "术语定义", "参考文献"],
            2: ["产品范围", "产品功能", "软件定位", "用户特征", "约束", "假设和依赖"],
            3: ["用户与角色", "核心业务流程", "异常与补偿"],
        }
        for index, candidate in enumerate(clause_orders.get(section_number, []), start=1):
            if normalized == candidate:
                return index
        return 9

    @staticmethod
    def _apply_patch_text(*, previous_text: str, patch: dict, content: str) -> PatchTextResult:
        operation = str(patch.get("operation") or "append_to_block")
        normalized_previous = previous_text.strip()
        normalized_content = content.strip()
        if operation in {"replace_range", "replace"}:
            return PatchTextResult(
                new_text=normalized_content,
                start_offset=0,
                end_offset=len(normalized_content),
                deleted_text=normalized_previous,
            )
        if operation in {"delete", "delete_range"}:
            if not normalized_previous or not normalized_content:
                return PatchTextResult(
                    new_text=normalized_previous,
                    start_offset=0,
                    end_offset=0,
                )
            start_offset = normalized_previous.find(normalized_content)
            if start_offset < 0:
                return PatchTextResult(
                    new_text=normalized_previous,
                    start_offset=0,
                    end_offset=0,
                )
            end_offset = start_offset + len(normalized_content)
            return PatchTextResult(
                new_text=f"{normalized_previous[:start_offset]}{normalized_previous[end_offset:]}",
                start_offset=start_offset,
                end_offset=start_offset,
                deleted_text=normalized_content,
            )
        if not normalized_previous:
            return PatchTextResult(
                new_text=normalized_content,
                start_offset=0,
                end_offset=len(normalized_content),
            )
        if normalized_content in normalized_previous:
            return PatchTextResult(
                new_text=normalized_previous,
                start_offset=0,
                end_offset=0,
            )
        appended = f"{normalized_previous}\n{normalized_content}"
        return PatchTextResult(
            new_text=appended,
            start_offset=len(normalized_previous) + 1,
            end_offset=len(appended),
        )

    @staticmethod
    def _anchor_path(*, patch: dict, projection_spec_node: dict, anchor_plan: dict | None = None) -> str:
        anchor_plan = dict(anchor_plan or {})
        return str(
            anchor_plan.get("anchor_path")
            or patch.get("anchor_path")
            or projection_spec_node.get("target_section")
            or projection_spec_node.get("node_id")
            or "未绑定模板章节"
        )

    @staticmethod
    def _hit_spec_nodes(*, patch: dict, projection_spec_node: dict, anchor_plan: dict | None = None) -> list[str]:
        candidates = patch.get("hit_spec_nodes")
        if isinstance(candidates, list):
            return [str(item) for item in candidates if str(item).strip()]
        node_id = str(projection_spec_node.get("node_id") or "").strip()
        if not node_id and anchor_plan:
            clause_id = str(anchor_plan.get("template_clause_id") or "").strip()
            node_id = f"SPEC-{clause_id}" if clause_id else ""
        return [node_id] if node_id else []

    @staticmethod
    def _append_unique(current: list[str], additions: list[str]) -> list[str]:
        result = list(current)
        for item in additions:
            if item and item not in result:
                result.append(item)
        return result

    @staticmethod
    def _turn_color_token(turn_id: str) -> str:
        try:
            index = int(turn_id.split("-")[-1])
        except ValueError:
            index = 1
        return f"turn-color-{((index - 1) % 8) + 1:02d}"

    @staticmethod
    def _current_patch_ids(*, patch_proposals: list[dict], anchor_path: str, turn_id: str) -> list[str]:
        result: list[str] = []
        for patch in patch_proposals:
            if str(patch.get("source_turn_id") or "") != turn_id:
                continue
            if str(patch.get("target_section") or "") != anchor_path:
                continue
            patch_id = str(patch.get("patch_id") or "").strip()
            if patch_id:
                result.append(patch_id)
        return result
