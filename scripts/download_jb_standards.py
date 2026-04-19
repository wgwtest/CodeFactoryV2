#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
LIB_ROOT = ROOT / "DOC" / "JB_DOC" / "99-标准来源库"
DETAIL_DIR = LIB_ROOT / "detail_pages"
RAW_DIR = LIB_ROOT / "raw"
META_DIR = LIB_ROOT / "metadata"
MANIFEST_PATH = LIB_ROOT / "manifest.json"

DETAIL_URL = "https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number={ident}"
WMX_URL = "https://quicksearch.dla.mil/WMX/Default.aspx?token={token}"


STANDARDS: list[dict[str, str]] = [
    {"code": "MIL-STD-498", "title": "Software Development and Documentation", "ident": "114847", "group": "lifecycle"},
    {"code": "DI-IPSC-81427", "title": "Software Development Plan", "ident": "205530", "group": "process"},
    {"code": "DI-SESS-81785", "title": "Systems Engineering Management Plan", "ident": "276889", "group": "process"},
    {"code": "DI-SESS-80858", "title": "Supplier's Configuration Management Plan", "ident": "118396", "group": "process"},
    {"code": "DI-QCIC-81794", "title": "Quality Assurance Program Plan", "ident": "275987", "group": "process"},
    {"code": "DI-QCIC-81795", "title": "Software Quality Assurance Report", "ident": "275988", "group": "process"},
    {"code": "DI-MGMT-82133", "title": "Requirements Traceability Verification Matrix", "ident": "282266", "group": "verification"},
    {"code": "DI-IPSC-81433", "title": "Software Requirements Specification", "ident": "205912", "group": "product"},
    {"code": "DI-IPSC-81434", "title": "Interface Requirements Specification", "ident": "205913", "group": "product"},
    {"code": "DI-IPSC-81435", "title": "Software Design Description", "ident": "205915", "group": "product"},
    {"code": "DI-IPSC-81436", "title": "Interface Design Description", "ident": "205916", "group": "product"},
    {"code": "DI-IPSC-81437", "title": "Database Design Description", "ident": "205914", "group": "product"},
    {"code": "DI-IPSC-81438", "title": "Software Test Plan", "ident": "205917", "group": "verification"},
    {"code": "DI-IPSC-81439", "title": "Software Test Description", "ident": "205918", "group": "verification"},
    {"code": "DI-IPSC-81440", "title": "Software Test Report", "ident": "205919", "group": "verification"},
    {"code": "DI-IPSC-81441", "title": "Software Product Specification", "ident": "205920", "group": "delivery"},
    {"code": "DI-IPSC-81442", "title": "Software Version Description", "ident": "205921", "group": "delivery"},
    {"code": "DI-IPSC-81429", "title": "Software Transition Plan", "ident": "205908", "group": "delivery"},
    {"code": "DI-IPSC-82259", "title": "Software/Hardware Requirements Specification", "ident": "283189", "group": "product"},
    {"code": "DI-IPSC-82284", "title": "Software/Hardware Design Description", "ident": "283271", "group": "product"},
]


def _build_session() -> requests.Session:
    session = requests.Session()
    proxy = os.environ.get("JB_STANDARD_PROXY") or "http://127.0.0.1:10809"
    if not os.environ.get("HTTP_PROXY") and not os.environ.get("HTTPS_PROXY"):
        session.proxies.update({"http": proxy, "https": proxy})
    session.headers.update(
        {
            "User-Agent": "CodeFactoryV2-StandardDownloader/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    return session


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")


def _extract_tokens(html: str) -> list[str]:
    tokens = re.findall(r"ImageRedirector\.aspx\?token=([0-9]+\.[0-9]+)", html)
    ordered: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered


def _extract_field(html: str, field_id: str) -> str | None:
    patterns = [
        rf'id="{field_id}"[^>]*>(.*?)</',
        rf'id="{field_id}"[^>]*value="(.*?)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            value = re.sub(r"<[^>]+>", " ", match.group(1))
            value = re.sub(r"\s+", " ", value).strip()
            if value:
                return value
    return None


def _save_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _save_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _download_wmx(session: requests.Session, code: str, token: str) -> dict[str, Any]:
    token_id = token.split(".")[0]
    response = session.get(WMX_URL.format(token=token_id), timeout=120)
    response.raise_for_status()

    ext = ".pdf" if response.content.startswith(b"%PDF") else ".html"
    filename = f"{_slug(code)}-token{token_id}{ext}"
    file_path = RAW_DIR / filename
    _save_bytes(file_path, response.content)

    return {
        "token": token,
        "token_id": token_id,
        "download_url": WMX_URL.format(token=token_id),
        "file": str(file_path.relative_to(ROOT)),
        "content_type": response.headers.get("content-type", ""),
        "size": len(response.content),
        "is_pdf": ext == ".pdf",
    }


def main() -> None:
    DETAIL_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)

    session = _build_session()
    manifest: list[dict[str, Any]] = []

    for standard in STANDARDS:
        code = standard["code"]
        ident = standard["ident"]
        detail_url = DETAIL_URL.format(ident=ident)

        detail_response = session.get(detail_url, timeout=60)
        detail_response.raise_for_status()
        html = detail_response.text

        detail_file = DETAIL_DIR / f"{_slug(code)}-{ident}.html"
        _save_text(detail_file, html)

        tokens = _extract_tokens(html)
        downloads = []
        for token in tokens:
            try:
                downloads.append(_download_wmx(session, code, token))
            except Exception as exc:  # noqa: BLE001
                downloads.append(
                    {
                        "token": token,
                        "token_id": token.split(".")[0],
                        "download_url": WMX_URL.format(token=token.split(".")[0]),
                        "error": str(exc),
                    }
                )

        metadata = {
            **standard,
            "detail_url": detail_url,
            "detail_file": str(detail_file.relative_to(ROOT)),
            "detail_title": _extract_field(html, "ControlBody_lblTitle"),
            "scope": _extract_field(html, "ControlBody_lblScope"),
            "status": _extract_field(html, "ControlBody_lblStatus"),
            "document_date": _extract_field(html, "ControlBody_lblDocumentDate"),
            "distribution": _extract_field(html, "ControlBody_lblDistribution"),
            "tokens": downloads,
        }
        meta_file = META_DIR / f"{_slug(code)}-{ident}.json"
        _save_text(meta_file, json.dumps(metadata, ensure_ascii=False, indent=2))
        metadata["metadata_file"] = str(meta_file.relative_to(ROOT))
        manifest.append(metadata)

    _save_text(MANIFEST_PATH, json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"Downloaded {len(manifest)} standard entries into {LIB_ROOT}")


if __name__ == "__main__":
    main()
