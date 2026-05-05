from __future__ import annotations

from dataclasses import dataclass


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
    ) -> WorkingDocumentUpdateResult:
        self._ensure_shape(working_document)
        before_excerpt = self.render_excerpt(working_document=working_document)
        applied_block_ids: list[str] = []
        applied_fragment_ids: list[str] = []
        changed_blocks: list[dict] = []

        for patch in document_patch:
            content = str(patch.get("content") or "").strip()
            if not content:
                continue
            anchor_path = self._anchor_path(patch=patch, projection_spec_node=projection_spec_node)
            block = self._find_or_create_block(working_document=working_document, anchor_path=anchor_path)
            previous_text = str(block.get("text") or "")
            patch_result = self._apply_patch_text(previous_text=previous_text, patch=patch, content=content)
            new_text = patch_result.new_text
            if new_text == previous_text:
                continue

            fragment_id = f"frag-{len(working_document['revision_fragments']) + 1:04d}"
            block["text"] = new_text
            block["last_turn_id"] = turn_id
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
                "hit_spec_nodes": self._hit_spec_nodes(patch=patch, projection_spec_node=projection_spec_node),
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
            anchor = str(block.get("anchor_path") or "").strip()
            lines.append(f"{anchor}\n{text}" if anchor else text)
        return "\n\n".join(lines)

    def _ensure_shape(self, working_document: dict) -> None:
        if "blocks" not in working_document:
            blocks = []
            for index, section in enumerate(list(working_document.get("sections", [])), start=1):
                content = str(section.get("content") or "").strip()
                if not content:
                    continue
                blocks.append(
                    {
                        "block_id": f"blk-{index:04d}",
                        "anchor_path": str(section.get("target_section") or section.get("section_id") or ""),
                        "block_type": "paragraph",
                        "order_index": index * 10,
                        "text": content,
                        "last_turn_id": section.get("last_turn_id"),
                        "source_fragment_ids": [],
                    }
                )
            working_document["blocks"] = blocks
        working_document.pop("sections", None)
        working_document.setdefault("revision_fragments", [])

    def _find_or_create_block(self, *, working_document: dict, anchor_path: str) -> dict:
        for block in working_document["blocks"]:
            if str(block.get("anchor_path") or "") == anchor_path:
                return block
        block = {
            "block_id": f"blk-{len(working_document['blocks']) + 1:04d}",
            "anchor_path": anchor_path,
            "block_type": "paragraph",
            "order_index": (len(working_document["blocks"]) + 1) * 10,
            "text": "",
            "last_turn_id": None,
            "source_fragment_ids": [],
        }
        working_document["blocks"].append(block)
        return block

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
    def _anchor_path(*, patch: dict, projection_spec_node: dict) -> str:
        return str(
            patch.get("anchor_path")
            or patch.get("section")
            or projection_spec_node.get("target_section")
            or projection_spec_node.get("node_id")
            or "未绑定模板章节"
        )

    @staticmethod
    def _hit_spec_nodes(*, patch: dict, projection_spec_node: dict) -> list[str]:
        candidates = patch.get("hit_spec_nodes")
        if isinstance(candidates, list):
            return [str(item) for item in candidates if str(item).strip()]
        node_id = str(projection_spec_node.get("node_id") or "").strip()
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
