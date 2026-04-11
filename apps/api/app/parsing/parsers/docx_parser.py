from docx import Document


def parse_docx(file_path: str) -> list[str]:
    document = Document(file_path)
    return [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
