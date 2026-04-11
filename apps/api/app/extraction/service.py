from app.extraction.rules import extract_candidates


class ExtractionService:
    def extract(self, segments):
        return extract_candidates(segments)
