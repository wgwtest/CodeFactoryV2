from pathlib import Path
import sys

from docx import Document

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts.build_archive_knowledge import collect_documents


def _create_docx(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    for line in lines:
        document.add_paragraph(line)
    document.save(path)


def test_collect_documents_prefers_live_source_paths_over_cached_duplicates(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    cache_root = tmp_path / "cache"

    live_doc = source_root / "20161116-chinese" / "[3]NAS体系结构产品" / "As Is" / "10002024.docx"
    cache_duplicate = (
        cache_root
        / "20161116╠σ╧╡╜ß╣╣╬─╧╫╖¡╥δ╗π╫▄"
        / "20161116╠σ╧╡╜ß╣╣╬─╧╫╖¡╥δ╗π╫▄"
        / "[3]NAS体系结构产品"
        / "As Is"
        / "10002024.docx"
    )
    cache_only_doc = cache_root / "2014-09-24-FAA NAS EA" / "As is" / "10002025.docx"

    _create_docx(live_doc, ["OV-2 当前状态", "塔台"])
    cache_duplicate.parent.mkdir(parents=True, exist_ok=True)
    cache_duplicate.write_bytes(live_doc.read_bytes())
    _create_docx(cache_only_doc, ["OV-5 当前活动模型"])

    documents = collect_documents([source_root, cache_root])

    assert [document.path for document in documents] == [
        "2014-09-24-FAA NAS EA/As is/10002025.docx",
        "20161116-chinese/[3]NAS体系结构产品/As Is/10002024.docx",
    ]
