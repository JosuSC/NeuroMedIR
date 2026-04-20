from dataclasses import dataclass
from typing import Dict, Optional

from .utils import text_fingerprint


@dataclass
class ValidationResult:
    is_valid: bool
    reason: Optional[str] = None


class CorpusQualityGate:
    def __init__(self, min_content_chars: int = 600):
        self.min_content_chars = min_content_chars
        self._seen_urls = set()
        self._seen_fingerprints = set()

    def register_existing(self, doc: Dict):
        url = str(doc.get("url", "")).strip().lower()
        content = str(doc.get("content", ""))
        if url:
            self._seen_urls.add(url)
        if content:
            self._seen_fingerprints.add(text_fingerprint(content))

    def validate(self, doc: Dict) -> ValidationResult:
        required = ["title", "content", "source", "url", "category", "language"]
        for field in required:
            value = doc.get(field)
            if not isinstance(value, str) or not value.strip():
                return ValidationResult(False, f"missing_or_empty_{field}")

        if doc["language"] not in {"en", "es"}:
            return ValidationResult(False, "invalid_language")

        if len(doc["content"]) < self.min_content_chars:
            return ValidationResult(False, "content_too_short")

        normalized_url = doc["url"].strip().lower()
        if normalized_url in self._seen_urls:
            return ValidationResult(False, "duplicate_url")

        fp = text_fingerprint(doc["content"])
        if fp in self._seen_fingerprints:
            return ValidationResult(False, "duplicate_content")

        self._seen_urls.add(normalized_url)
        self._seen_fingerprints.add(fp)
        return ValidationResult(True, None)
