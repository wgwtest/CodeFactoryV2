import fitz


def parse_pdf(file_path: str) -> list[tuple[int, str]]:
    document = fitz.open(file_path)
    return [(page.number + 1, page.get_text("text")) for page in document]
