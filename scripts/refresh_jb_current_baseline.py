#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
LIB_ROOT = ROOT / "DOC" / "JB_DOC" / "99-标准来源库"
DETAIL_DIR = LIB_ROOT / "detail_pages"
RAW_DIR = LIB_ROOT / "raw"
META_DIR = LIB_ROOT / "metadata"
MANIFEST_PATH = LIB_ROOT / "manifest.json"
SUMMARY_PATH = LIB_ROOT / "01-current-baseline修订证据说明.md"


CURRENT_BASELINE: list[dict[str, Any]] = [
    {
        "code": "DI-IPSC-81427B",
        "title": "Software Development Plan",
        "group": "process",
        "base_code": "DI-IPSC-81427",
        "ident": "205530",
        "detail_url": "https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=205530",
        "detail_file": "DOC/JB_DOC/99-标准来源库/detail_pages/DI-IPSC-81427-205530.html",
        "detail_title": "Software Development Plan (SDP)",
        "status": "Active",
        "document_date": "13-MAR-2017",
        "notes": "QuickSearch 详情页仍挂主号 `DI-IPSC-81427`，current baseline revision 以官方 PDF 头部的 `Number: DI-IPSC-81427B` 为准。",
        "evidence": [
            {
                "label": "official_revision_pdf",
                "url": "https://quicksearch.dla.mil/WMX/Default.aspx?token=5746250",
                "filename": "DI-IPSC-81427B-token5746250.pdf",
                "kind": "official_pdf",
            }
        ],
    },
    {
        "code": "DI-SESS-81785B",
        "title": "Systems Engineering Management Plan",
        "group": "process",
        "base_code": "DI-SESS-81785",
        "ident": "276889",
        "detail_url": "https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=276889",
        "detail_file": "DOC/JB_DOC/99-标准来源库/detail_pages/DI-SESS-81785-276889.html",
        "detail_title": "Systems Engineering Management Plan (SEMP)",
        "status": "Active",
        "document_date": "08-JAN-2025",
        "notes": "QuickSearch 详情页已更新到 2025 版 DID Date；官方 PDF 头部给出 `Number: DI-SESS-81785B`。",
        "evidence": [
            {
                "label": "official_revision_pdf",
                "url": "https://quicksearch.dla.mil/WMX/Default.aspx?token=5792932",
                "filename": "DI-SESS-81785B-token5792932.pdf",
                "kind": "official_pdf",
            }
        ],
    },
    {
        "code": "DI-SESS-80858D",
        "title": "Supplier's Configuration Management Plan",
        "group": "process",
        "base_code": "DI-SESS-80858",
        "ident": None,
        "detail_url": None,
        "detail_file": None,
        "detail_title": "Supplier's Configuration Management Plan",
        "status": "Validated for use in acquisition (NOTICE 1, 12-MAY-2025)",
        "document_date": "11-FEB-2020",
        "notes": "稳定的 QuickSearch 详情页当前不可公开访问，改以官方 revision D PDF 与 NOTICE 1 作为 current baseline 证据。",
        "evidence": [
            {
                "label": "official_revision_pdf",
                "url": "https://quicksearch.dla.mil/WMX/Default.aspx?token=5763549",
                "filename": "DI-SESS-80858D-token5763549.pdf",
                "kind": "official_pdf",
            },
            {
                "label": "official_validation_notice",
                "url": "https://quicksearch.dla.mil/WMX/Default.aspx?token=5794369",
                "filename": "DI-SESS-80858D-NOTICE1-token5794369.pdf",
                "kind": "official_notice",
            },
        ],
    },
    {
        "code": "DI-QCIC-81794A",
        "title": "Quality Assurance Program Plan",
        "group": "process",
        "base_code": "DI-QCIC-81794",
        "ident": None,
        "detail_url": None,
        "detail_file": None,
        "detail_title": "Quality Assurance Program Plan (QAPP)",
        "status": "Official revision A PDF archived",
        "document_date": "16-SEP-2019",
        "notes": "旧 `DI-QCIC-81794` QuickSearch 详情页本地归档已错指到无关 ASTM 文档，current baseline 改由官方 revision A PDF 直接建档。",
        "evidence": [
            {
                "label": "official_revision_pdf",
                "url": "https://quicksearch.dla.mil/WMX/Default.aspx?token=5761211",
                "filename": "DI-QCIC-81794A-token5761211.pdf",
                "kind": "official_pdf",
            }
        ],
    },
]

LEGACY_BASE_OVERRIDES: dict[str, dict[str, Any]] = {
    "DI-IPSC-81427": {
        "source_mode": "legacy_base_entry",
        "legacy_status_note": "主号详情页保留；current baseline 请改看 `DI-IPSC-81427B` revision 证据条目。",
        "current_baseline_revision": "DI-IPSC-81427B",
    },
    "DI-SESS-81785": {
        "source_mode": "legacy_base_entry",
        "legacy_status_note": "主号详情页保留；current baseline 请改看 `DI-SESS-81785B` revision 证据条目。",
        "current_baseline_revision": "DI-SESS-81785B",
    },
    "DI-SESS-80858": {
        "source_mode": "legacy_base_entry_stale",
        "legacy_status_note": "旧主号页无法稳定公开访问；current baseline 请改看 `DI-SESS-80858D` revision PDF + NOTICE 1 证据条目。",
        "current_baseline_revision": "DI-SESS-80858D",
    },
    "DI-QCIC-81794": {
        "source_mode": "legacy_base_entry_invalid",
        "legacy_status_note": "旧主号页本地归档已错指到 ASTM-D2400；current baseline 请改看 `DI-QCIC-81794A` revision PDF 证据条目。",
        "current_baseline_revision": "DI-QCIC-81794A",
    },
}


def _build_session() -> requests.Session:
    session = requests.Session()
    proxy = os.environ.get("JB_STANDARD_PROXY") or "http://127.0.0.1:10809"
    if not os.environ.get("HTTP_PROXY") and not os.environ.get("HTTPS_PROXY"):
        session.proxies.update({"http": proxy, "https": proxy})
    session.headers.update(
        {
            "User-Agent": "CodeFactoryV2-CurrentBaselineRefresher/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    return session


def _save_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _save_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _relative(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path.relative_to(ROOT))


def _extract_pdf_excerpt(path: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["pdftotext", str(path), "-"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {"excerpt_lines": [], "number": None, "approval_date": None}

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    excerpt_lines = lines[:20]
    number = None
    approval_date = None
    for line in lines[:40]:
        if number is None:
            match = re.match(r"^Number:\s*(.+)$", line)
            if match:
                number = match.group(1).strip()
        if approval_date is None:
            match = re.match(r"^Approval Date:\s*(.+)$", line)
            if match:
                approval_date = match.group(1).strip()
    return {
        "excerpt_lines": excerpt_lines,
        "number": number,
        "approval_date": approval_date,
    }


def _download_evidence(session: requests.Session, item: dict[str, str]) -> dict[str, Any]:
    url = item["url"]
    filename = item["filename"]
    target = RAW_DIR / filename
    response = session.get(url, timeout=120)
    response.raise_for_status()
    _save_bytes(target, response.content)

    parsed = _extract_pdf_excerpt(target)
    return {
        "label": item["label"],
        "kind": item["kind"],
        "download_url": url,
        "file": _relative(target),
        "content_type": response.headers.get("content-type", ""),
        "size": len(response.content),
        "is_pdf": response.content.startswith(b"%PDF"),
        "extracted_number": parsed["number"],
        "extracted_approval_date": parsed["approval_date"],
        "excerpt_lines": parsed["excerpt_lines"],
    }


def _build_metadata(entry: dict[str, Any], downloads: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "code": entry["code"],
        "title": entry["title"],
        "group": entry["group"],
        "base_code": entry.get("base_code"),
        "ident": entry.get("ident"),
        "detail_url": entry.get("detail_url"),
        "detail_file": entry.get("detail_file"),
        "detail_title": entry.get("detail_title"),
        "scope": None,
        "status": entry.get("status"),
        "document_date": entry.get("document_date"),
        "distribution": None,
        "source_mode": "current_baseline_revision_evidence",
        "notes": entry.get("notes"),
        "archived_at": datetime.now(UTC).isoformat(),
        "tokens": downloads,
    }


def _load_manifest() -> list[dict[str, Any]]:
    if not MANIFEST_PATH.exists():
        return []
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _update_legacy_base_entries(entries: dict[str, dict[str, Any]]) -> None:
    for code, patch in LEGACY_BASE_OVERRIDES.items():
        entry = entries.get(code)
        if not entry:
            continue
        entry.update(patch)
        metadata_file = entry.get("metadata_file")
        if metadata_file:
            meta_path = ROOT / metadata_file
            if meta_path.exists():
                payload = json.loads(meta_path.read_text(encoding="utf-8"))
                payload.update(patch)
                _save_text(meta_path, json.dumps(payload, ensure_ascii=False, indent=2))


def _write_summary(entries: list[dict[str, Any]]) -> None:
    lines = [
        "# Current Baseline 修订证据说明",
        "",
        "本文件记录 `99-标准来源库/` 中与平台 current baseline 对齐的 revision 级官方证据条目。",
        "",
        "## 1. 说明",
        "",
        "- 这些条目不替代旧主号页归档，而是补充 revision 级权威证据。",
        "- 能直接访问稳定 `QuickSearch` 详情页的对象，继续保留详情页 + 官方 PDF 双证据。",
        "- 无法稳定访问详情页的对象，改用官方 `WMX` PDF 或 `NOTICE` 建档，并在元数据中说明原因。",
        "",
        "## 2. 当前条目",
        "",
        "| 代码 | 类型 | 本地证据 | 当前状态 | 备注 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in entries:
        files = "<br/>".join(f"`{Path(item['file']).name}`" for item in entry["tokens"])
        notes = entry.get("notes", "")
        lines.append(f"| `{entry['code']}` | `{entry['group']}` | {files} | {entry.get('status') or ''} | {notes} |")
    lines.extend(
        [
            "",
            "## 3. 与主号页的关系",
            "",
            "- `DI-IPSC-81427B` 继续引用主号页 `DI-IPSC-81427` 的详情归档。",
            "- `DI-SESS-81785B` 继续引用主号页 `DI-SESS-81785` 的详情归档。",
            "- `DI-SESS-80858D` 与 `DI-QCIC-81794A` 当前以官方 revision 级 PDF / notice 为主证据，不再依赖旧主号页作为 current baseline 依据。",
        ]
    )
    _save_text(SUMMARY_PATH, "\n".join(lines) + "\n")


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)
    session = _build_session()
    manifest = _load_manifest()
    existing_by_code = {entry["code"]: entry for entry in manifest}

    written_entries: list[dict[str, Any]] = []
    for entry in CURRENT_BASELINE:
        downloads = [_download_evidence(session, item) for item in entry["evidence"]]
        metadata = _build_metadata(entry, downloads)
        meta_path = META_DIR / f"{entry['code']}-current-baseline.json"
        _save_text(meta_path, json.dumps(metadata, ensure_ascii=False, indent=2))
        metadata["metadata_file"] = _relative(meta_path)
        existing_by_code[entry["code"]] = metadata
        written_entries.append(metadata)

    _update_legacy_base_entries(existing_by_code)

    ordered_manifest: list[dict[str, Any]] = []
    seen: set[str] = set()
    original_codes = [entry["code"] for entry in manifest]
    for code in original_codes + [entry["code"] for entry in CURRENT_BASELINE]:
        if code in seen:
            continue
        seen.add(code)
        ordered_manifest.append(existing_by_code[code])

    _save_text(MANIFEST_PATH, json.dumps(ordered_manifest, ensure_ascii=False, indent=2))
    _write_summary(written_entries)
    print(f"Refreshed {len(written_entries)} current baseline evidence entries.")


if __name__ == "__main__":
    main()
