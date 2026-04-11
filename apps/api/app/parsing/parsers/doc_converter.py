import subprocess
from pathlib import Path


def convert_doc_to_docx(file_path: str, output_dir: str) -> str:
    subprocess.run(
        ["soffice", "--headless", "--convert-to", "docx", file_path, "--outdir", output_dir],
        check=True,
    )
    return str(Path(output_dir) / (Path(file_path).stem + ".docx"))
