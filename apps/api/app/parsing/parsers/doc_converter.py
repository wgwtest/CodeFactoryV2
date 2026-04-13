import subprocess
from pathlib import Path


def convert_doc_to_docx(file_path: str, output_dir: str) -> str:
    return convert_office_document(file_path, output_dir, "docx")


def convert_office_document(file_path: str, output_dir: str, target_format: str) -> str:
    subprocess.run(
        ["soffice", "--headless", "--convert-to", target_format, file_path, "--outdir", output_dir],
        check=True,
    )
    return str(Path(output_dir) / f"{Path(file_path).stem}.{target_format}")
