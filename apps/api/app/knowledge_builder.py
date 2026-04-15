from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import md5
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.extraction.service import ExtractionService
    from app.parsing.models import ParsedSegment


ACRONYM_PATTERN = re.compile(
    r"(?P<name>[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9/\-—·、,. ]{1,80}?)\s*[（(](?P<acronym>[A-Z][A-Z0-9\- ]{1,24})[)）]"
)
ARTIFACT_PATTERN = re.compile(r"\b(?:AV|OV|SV|TV)-\d(?:-\d)?\b", re.IGNORECASE)
TABLE_DIVIDER_PATTERN = re.compile(r"^[\-: ]+$")
IO_EN_PATTERN = re.compile(r"I/O\s*\d+\s*(.+?)(?=\s*I/O\s*\d+|$)", re.IGNORECASE)
IO_ZH_PATTERN = re.compile(r"输入/输出\s*\d+[：:]\s*(.+?)(?=\s*输入/输出\s*\d+[：:]|$)")
IEX_NAME_EN_PATTERN = re.compile(r"IEX\s*Name\s*[:：]\s*(.+)$", re.IGNORECASE)
IEX_NAME_ZH_PATTERN = re.compile(r"IEX\s*名称\s*[:：]\s*(.+)$", re.IGNORECASE)
INTERACTION_PAIR_PATTERN = re.compile(r"^(?P<source>[A-Za-z/]+)\s*-\s*(?P<target>[A-Za-z/]+)(?:\s+|$)", re.IGNORECASE)

SERVICE_NAMES = {
    "使命任务服务",
    "支持服务",
    "SOA核心服务",
    "管理服务",
    "企业治理",
    "技术体系架构服务",
    "交互服务",
    "发布/订阅服务",
    "信息安全服务",
    "接口管理",
}

GENERIC_NAME_EXACT = {
    "description",
    "view",
    "summary information",
}

GENERIC_NAME_PREFIXES = (
    "本文档",
    "the purpose of",
    "and the",
    "it ",
    "它按照",
)

PROCESS_RULES = {
    "服务互操作流程": ["服务互操作性过程流", "service interoperability process flow"],
    "集成系统工程": ["集成系统工程框架", "integrated systems engineering framework"],
    "架构与需求治理": [
        "管理和控制nas架构与需求",
        "managing and controlling the nas architecture and requirements",
        "architecture and requirements",
    ],
    "需求到采购衔接": ["采购活动", "procurement"],
    "服务演进路线图规划": ["路线图", "roadmap"],
    "运行活动建模": ["ov-5"],
}

EVENT_RULES = {
    "当前状态（As Is）": ["as is"],
    "中期演进（Mid Term）": ["mid term", "中期"],
    "远期目标（Far Term）": ["far term", "远期"],
    "2025 NextGen目标": ["2025", "nextgen"],
}

OPERATIONAL_NODE_TOKEN_MAP = {
    "ATCT": "机场塔台管制",
    "TOWER": "机场塔台管制",
    "AIRCRAFT": "航空器",
    "ARTCC": "区域管制中心",
    "TRACON": "终端雷达进近管制",
    "ATCSCC": "国家流量管理中心",
    "FSS/AFSS": "飞行服务站/自动飞行服务站",
    "FSS": "飞行服务站/自动飞行服务站",
    "AFSS": "飞行服务站/自动飞行服务站",
}

OPERATIONAL_NODE_ALIASES = {
    "机场塔台管制": ["ATCT", "Tower", "塔台"],
    "航空器": ["Aircraft"],
    "区域管制中心": ["ARTCC"],
    "终端雷达进近管制": ["TRACON", "Tracon"],
    "国家流量管理中心": ["ATCSCC"],
    "飞行服务站/自动飞行服务站": ["FSS/AFSS"],
}

SKIP_PREFIXES = ("图", "表", "附件", "版本", "page", "version", "目  录", "图目录", "表目录")


@dataclass(slots=True)
class SourceDocument:
    path: str
    title: str
    file_type: str
    source_archive: str
    text: str
    parser_name: str | None = None
    segment_count: int = 0
    segments: list["ParsedSegment"] | None = None
    source_file_path: str | None = None


def build_knowledge_index(
    documents: list[SourceDocument],
    extraction_service: "ExtractionService | None" = None,
    diagnostics_collector: list[dict] | None = None,
) -> dict:
    nodes: dict[tuple[str, str], dict] = {}
    relations: list[dict[str, str]] = []
    relation_keys: set[tuple[str, str, str]] = set()
    document_rows: list[dict[str, str | int]] = []
    known_item_ids_by_name: dict[str, str] = {}
    known_item_ids_by_alias: dict[str, str] = {}

    for document in documents:
        doc_id = _document_id(document.path)
        document_rows.append(
            {
                "id": doc_id,
                "path": document.path,
                "title": document.title,
                "file_type": document.file_type,
                "source_archive": document.source_archive,
                "character_count": len(document.text),
            }
        )

        batch = _extract_document_knowledge(document, doc_id, extraction_service)
        if diagnostics_collector is not None:
            diagnostics_collector.append(
                {
                    "document_id": doc_id,
                    "title": document.title,
                    "file_path": document.path,
                    "file_type": document.file_type,
                    "parser_name": document.parser_name,
                    "segment_count": document.segment_count or len(document.segments or []),
                    "strategy": batch.strategy,
                    "candidate_count": len(batch.candidates),
                    "relation_count": len(batch.relations),
                    "llm_enrichment_used": bool(batch.metadata.get("llm_enrichment_used")),
                    "llm_provider": batch.metadata.get("llm_provider"),
                    "llm_model": batch.metadata.get("llm_model"),
                    "llm_base_url": batch.metadata.get("llm_base_url"),
                    "chunking_used": bool(batch.metadata.get("chunking_used")),
                    "chunk_count": batch.metadata.get("chunk_count"),
                    "chunk_char_limit": batch.metadata.get("chunk_char_limit"),
                    "chunk_candidate_count_total": batch.metadata.get("chunk_candidate_count_total"),
                    "chunk_relation_count_total": batch.metadata.get("chunk_relation_count_total"),
                    "merged_candidate_count": batch.metadata.get("merged_candidate_count"),
                    "merged_relation_count": batch.metadata.get("merged_relation_count"),
                }
            )
        local_item_ids_by_name: dict[str, str] = {}
        local_item_ids_by_alias: dict[str, str] = {}

        for candidate in batch.candidates:
            item_kind = _normalize_item_kind(candidate.item_type)
            item = {
                "name": candidate.canonical_name,
                "category": candidate.payload.get("category", _default_category(item_kind)),
                "aliases": candidate.payload.get("aliases", []),
                "evidence": candidate.payload.get("evidence") or document.title,
            }
            node_id = _merge_node(nodes, item_kind, item, doc_id)
            local_item_ids_by_name[item["name"]] = node_id
            local_item_ids_by_alias[_slug(item["name"])] = node_id
            known_item_ids_by_name[item["name"]] = node_id
            known_item_ids_by_alias[_slug(item["name"])] = node_id
            for alias in item.get("aliases", []):
                alias_slug = _slug(alias)
                local_item_ids_by_alias.setdefault(alias_slug, node_id)
                known_item_ids_by_alias.setdefault(alias_slug, node_id)
            _add_relation(relations, relation_keys, "document_mentions", doc_id, node_id)

        for relation in batch.relations:
            source_id = _resolve_item_id(
                relation.source_name,
                local_item_ids_by_name,
                local_item_ids_by_alias,
                known_item_ids_by_name,
                known_item_ids_by_alias,
            )
            target_id = _resolve_item_id(
                relation.target_name,
                local_item_ids_by_name,
                local_item_ids_by_alias,
                known_item_ids_by_name,
                known_item_ids_by_alias,
            )
            if source_id is None or target_id is None or source_id == target_id:
                continue
            _add_relation(
                relations,
                relation_keys,
                relation.relation_type,
                source_id,
                target_id,
                confidence=relation.confidence,
                evidence=relation.payload.get("evidence"),
            )

    entities = _finalize_nodes(nodes, "entity")
    events = _finalize_nodes(nodes, "event")
    processes = _finalize_nodes(nodes, "process")

    return {
        "documents": sorted(document_rows, key=lambda item: item["path"]),
        "entities": entities,
        "events": events,
        "processes": processes,
        "relations": sorted(relations, key=lambda item: (item["type"], item["from"], item["to"])),
        "summary": {
            "document_count": len(document_rows),
            "entity_count": len(entities),
            "event_count": len(events),
            "process_count": len(processes),
            "relation_count": len(relations),
        },
    }


def _extract_document_knowledge(
    document: SourceDocument,
    doc_id: str,
    extraction_service: "ExtractionService | None",
):
    from app.extraction.rules import extract_document_batch

    if extraction_service is None:
        from app.extraction.service import ExtractionService

        extraction_service = ExtractionService()

    segments = document.segments or _segments_from_text(document.text)
    if not segments:
        return extract_document_batch(document_id=doc_id, document=document, segments=[])

    return extraction_service.extract_document(
        document_id=doc_id,
        title=document.title,
        file_path=document.path,
        segments=segments,
    )


def _extract_entities(document: SourceDocument, lines: list[str], interactions: list[dict]) -> list[dict]:
    text = "\n".join(lines)
    found: dict[str, dict] = {}

    if (
        "国家空域系统" in document.title
        or "NAS" in document.title.upper()
        or "国家空域系统" in text[:1000]
        or "NAS" in document.path.upper()
    ):
        found.setdefault(
            "国家空域系统",
            {
                "name": "国家空域系统",
                "category": "system_or_service",
                "aliases": ["NAS"],
                "evidence": document.title,
            },
        )
    if "联邦航空管理局" in text[:1000] or "FAA" in text[:1000].upper():
        found.setdefault(
            "联邦航空管理局",
            {
                "name": "联邦航空管理局",
                "category": "organization",
                "aliases": ["FAA"],
                "evidence": document.title,
            },
        )

    for code in sorted({match.upper() for match in ARTIFACT_PATTERN.findall(f"{document.title}\n{text[:3000]}")}):
        found[code] = {
            "name": code,
            "category": "architecture_artifact",
            "aliases": [document.title] if code in document.title.upper() else [],
            "evidence": code,
        }

    for line in lines[:300]:
        lowered = line.lower()
        for service_name in SERVICE_NAMES:
            if service_name.lower() in lowered:
                found.setdefault(
                    service_name,
                    {
                        "name": service_name,
                        "category": "service_taxonomy",
                        "aliases": [],
                        "evidence": line,
                    },
                )

        for match in ACRONYM_PATTERN.finditer(line):
            name = _clean_phrase(match.group("name"))
            acronym = _clean_phrase(match.group("acronym"))
            if not _valid_phrase(name) or not _valid_phrase(acronym):
                continue
            if acronym in {"AV", "OV", "SV", "TV"} and (
                name.endswith("视角") or name.lower().endswith("view") or name.lower().endswith("views")
            ):
                continue
            entry = found.setdefault(
                name,
                {
                    "name": name,
                    "category": _classify_entity(name, acronym),
                    "aliases": [],
                    "evidence": line,
                },
            )
            if acronym not in entry["aliases"]:
                entry["aliases"].append(acronym)

    for line in lines[:1200]:
        cells = _split_table_row(line)
        if not cells or _is_table_divider(cells):
            continue

        node = _extract_operational_node(cells)
        if node is not None:
            _merge_extracted_entity(found, node["name"], node["category"], node["aliases"], line)

        iex_entity = _extract_iex_entity(cells)
        if iex_entity is not None:
            _merge_extracted_entity(found, iex_entity["name"], iex_entity["category"], iex_entity["aliases"], line)

    for interaction in interactions:
        for endpoint in (interaction["source_name"], interaction["target_name"]):
            _merge_extracted_entity(
                found,
                endpoint,
                "operational_node",
                OPERATIONAL_NODE_ALIASES.get(endpoint, []),
                interaction["evidence"],
            )

        for exchange in interaction["exchanges"]:
            _merge_extracted_entity(
                found,
                exchange["name"],
                "information_exchange",
                exchange["aliases"],
                interaction["evidence"],
            )

    return list(found.values())


def _extract_events(document: SourceDocument, lines: list[str]) -> list[dict]:
    search_space = f"{document.path}\n{document.title}\n" + "\n".join(lines[:120])
    lowered = search_space.lower()
    events = []
    for name, patterns in EVENT_RULES.items():
        if all(token in lowered for token in [patterns[0]]) or any(token in lowered for token in patterns):
            events.append({"name": name, "category": "timeline_event", "aliases": [], "evidence": document.title})
    return events


def _extract_processes(document: SourceDocument, lines: list[str]) -> list[dict]:
    search_space = f"{document.title}\n" + "\n".join(lines[:240])
    lowered = search_space.lower()
    found: dict[str, dict] = {}
    for name, patterns in PROCESS_RULES.items():
        if any(pattern in lowered for pattern in patterns):
            found[name] = {"name": name, "category": "domain_process", "aliases": [], "evidence": document.title}

    if "ov-5" in lowered or "运行活动模型" in search_space:
        for line in lines[:1600]:
            cells = _split_table_row(line)
            if len(cells) < 2 or _is_table_divider(cells):
                continue

            english_name = _clean_phrase(cells[0])
            chinese_name = _clean_phrase(cells[1])
            if not _looks_like_activity_name(english_name, chinese_name):
                continue

            found.setdefault(
                chinese_name,
                {
                    "name": chinese_name,
                    "category": "domain_process",
                    "aliases": [english_name] if english_name and english_name != chinese_name else [],
                    "evidence": line,
                },
            )

    return list(found.values())


def _extract_operational_interactions(lines: list[str]) -> list[dict]:
    interactions: list[dict] = []
    for line in lines[:1200]:
        cells = _split_table_row(line)
        if len(cells) < 2 or _is_table_divider(cells):
            continue

        token_match = INTERACTION_PAIR_PATTERN.match(cells[0])
        if token_match is None:
            continue

        source_name = _canonicalize_operational_node_token(token_match.group("source"))
        target_name = _canonicalize_operational_node_token(token_match.group("target"))
        if source_name is None or target_name is None:
            continue

        zh_exchanges = [_clean_phrase(match) for match in IO_ZH_PATTERN.findall(cells[1]) if _valid_phrase(_clean_phrase(match))]
        en_exchanges = [_clean_phrase(match) for match in IO_EN_PATTERN.findall(cells[0]) if _valid_phrase(_clean_phrase(match))]
        exchanges = []
        for index, name in enumerate(zh_exchanges):
            aliases = []
            if index < len(en_exchanges) and en_exchanges[index] != name:
                aliases.append(en_exchanges[index])
            exchanges.append({"name": name, "aliases": aliases})

        interactions.append(
            {
                "source_name": source_name,
                "target_name": target_name,
                "exchanges": exchanges,
                "evidence": cells[1],
            }
        )
    return interactions


def _extract_operational_node(cells: list[str]) -> dict | None:
    if len(cells) < 2:
        return None

    token = _normalize_operational_node_token(cells[0])
    canonical_name = _canonicalize_operational_node_token(token)
    if canonical_name is None:
        return None

    name = _clean_phrase(cells[1])
    if not _valid_phrase(name):
        return None

    aliases = [token, *OPERATIONAL_NODE_ALIASES.get(canonical_name, [])]
    aliases = [alias for alias in aliases if alias and alias != name]
    if name != canonical_name:
        aliases = [name, *aliases]

    return {
        "name": canonical_name,
        "category": "operational_node",
        "aliases": _dedupe_list(aliases),
    }


def _extract_iex_entity(cells: list[str]) -> dict | None:
    english_match = IEX_NAME_EN_PATTERN.search(cells[0]) if cells else None
    chinese_match = IEX_NAME_ZH_PATTERN.search(cells[1]) if len(cells) > 1 else None
    if english_match is None and chinese_match is None:
        return None

    name = _clean_phrase(chinese_match.group(1) if chinese_match else english_match.group(1))
    alias = _clean_phrase(english_match.group(1)) if english_match else None
    if not _valid_phrase(name):
        return None

    aliases = [alias] if alias and alias != name else []
    return {"name": name, "category": "information_exchange", "aliases": aliases}


def _merge_extracted_entity(found: dict[str, dict], name: str, category: str, aliases: list[str], evidence: str) -> None:
    entry = found.setdefault(
        name,
        {
            "name": name,
            "category": category,
            "aliases": [],
            "evidence": evidence,
        },
    )
    for alias in aliases:
        if alias not in entry["aliases"]:
            entry["aliases"].append(alias)


def _merge_node(nodes: dict[tuple[str, str], dict], kind: str, item: dict, doc_id: str) -> str:
    key = (kind, _slug(item["name"]))
    node = nodes.setdefault(
        key,
        {
            "id": f"{kind}-{_slug(item['name'])}",
            "kind": kind,
            "name": item["name"],
            "category": item["category"],
            "aliases": set(),
            "documents": set(),
            "evidence": [],
        },
    )
    node["aliases"].update(item.get("aliases", []))
    node["documents"].add(doc_id)
    evidence = item.get("evidence")
    if evidence and evidence not in [entry["excerpt"] for entry in node["evidence"]]:
        node["evidence"].append({"document_id": doc_id, "excerpt": evidence[:240]})
    return node["id"]


def _finalize_nodes(nodes: dict[tuple[str, str], dict], kind: str) -> list[dict]:
    finalized = []
    for (_, _), node in nodes.items():
        if node["kind"] != kind:
            continue
        finalized.append(
            {
                "id": node["id"],
                "name": node["name"],
                "category": node["category"],
                "aliases": sorted(node["aliases"]),
                "document_ids": sorted(node["documents"]),
                "evidence": node["evidence"][:5],
            }
        )
    return sorted(finalized, key=lambda item: (-len(item["document_ids"]), item["name"]))


def _default_category(item_kind: str) -> str:
    return {
        "entity": "domain_concept",
        "event": "timeline_event",
        "process": "domain_process",
    }.get(item_kind, "domain_concept")


def _normalize_item_kind(item_type: str) -> str:
    if item_type in {"entity", "event", "process"}:
        return item_type
    return "entity"


def _resolve_item_id(
    name: str,
    local_item_ids_by_name: dict[str, str],
    local_item_ids_by_alias: dict[str, str],
    known_item_ids_by_name: dict[str, str],
    known_item_ids_by_alias: dict[str, str],
) -> str | None:
    return (
        local_item_ids_by_name.get(name)
        or local_item_ids_by_alias.get(_slug(name))
        or known_item_ids_by_name.get(name)
        or known_item_ids_by_alias.get(_slug(name))
    )


def _add_relation(
    relations: list[dict[str, str]],
    relation_keys: set[tuple[str, str, str]],
    relation_type: str,
    from_id: str,
    to_id: str,
    *,
    confidence: float | None = None,
    evidence: str | None = None,
) -> None:
    key = (relation_type, from_id, to_id)
    if key in relation_keys:
        if confidence is None and evidence is None:
            return
        for relation in relations:
            if relation["type"] != relation_type or relation["from"] != from_id or relation["to"] != to_id:
                continue
            if confidence is not None:
                relation["confidence"] = max(confidence, float(relation.get("confidence", 0)))
            if evidence and not relation.get("evidence"):
                relation["evidence"] = evidence
        return
    relation_keys.add(key)
    relation: dict[str, str | float] = {"type": relation_type, "from": from_id, "to": to_id}
    if confidence is not None:
        relation["confidence"] = confidence
    if evidence:
        relation["evidence"] = evidence
    relations.append(relation)


def _resolve_entity_id(name: str, entity_ids_by_name: dict[str, str], entity_ids_by_alias: dict[str, str]) -> str | None:
    return entity_ids_by_name.get(name) or entity_ids_by_alias.get(_slug(name))


def _segments_from_text(text: str) -> list["ParsedSegment"]:
    from app.parsing.models import ParsedSegment

    segments: list[ParsedSegment] = []
    for index, line in enumerate((line.strip() for line in text.splitlines()), start=1):
        if not line:
            continue
        segments.append(
            ParsedSegment(
                heading=line[:255],
                content=line,
                anchor={"page": 1, "section": line[:255], "line_start": index, "line_end": index},
                block_type="table_row" if line.startswith("|") else "paragraph",
            )
        )
    return segments


def _classify_entity(name: str, acronym: str) -> str:
    lowered = f"{name} {acronym}".lower()
    if any(token in lowered for token in ("faa", "icao", "sesar", "办公室", "office", "管理局")):
        return "organization"
    if any(token in lowered for token in ("framework", "体系架构", "architecture", "ea", "isef", "naseaf")):
        return "architecture_concept"
    if any(token in lowered for token in ("service", "服务", "system", "系统", "program", "程序")):
        return "system_or_service"
    return "domain_concept"


def _document_id(path: str) -> str:
    return f"doc-{md5(path.encode('utf-8')).hexdigest()[:12]}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value.lower()).strip("-")
    return slug or "item"


def _clean_phrase(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" ，。;；:：()（）|"))


def _valid_phrase(value: str) -> bool:
    if len(value) < 2 or len(value) > 60:
        return False
    if value.lower().startswith(SKIP_PREFIXES):
        return False
    if value[0].isdigit():
        return False
    lowered = value.lower()
    if lowered in GENERIC_NAME_EXACT:
        return False
    if any(lowered.startswith(prefix) for prefix in GENERIC_NAME_PREFIXES):
        return False
    return True


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or stripped.count("|") < 3:
        return []
    return [_clean_phrase(part) for part in stripped.strip("|").split("|")]


def _is_table_divider(cells: list[str]) -> bool:
    return bool(cells) and all(TABLE_DIVIDER_PATTERN.fullmatch(cell or "") for cell in cells)


def _normalize_operational_node_token(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def _canonicalize_operational_node_token(value: str) -> str | None:
    return OPERATIONAL_NODE_TOKEN_MAP.get(_normalize_operational_node_token(value))


def _dedupe_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _looks_like_activity_name(english_name: str, chinese_name: str) -> bool:
    if not _valid_phrase(chinese_name):
        return False
    upper = english_name.upper()
    activity_tokens = (
        "MANAGE",
        "PLAN",
        "CONTROL",
        "ADVISE",
        "ALLOCATE",
        "DEVELOP",
        "TRACK",
        "SEPARATE",
        "SYNCHRONIZE",
        "TRANSFER",
        "PROVIDE",
        "MONITOR",
        "REQUEST",
    )
    return any(token in upper for token in activity_tokens)
