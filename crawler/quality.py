from dataclasses import dataclass
from typing import Dict, Optional

from .utils import text_fingerprint


"""
quality.py — Reglas simples de calidad para el corpus.

Prefiero que esta lógica sea transparente: si un documento se rechaza,
quiero poder decir rápidamente si fue por idioma, duplicado, URL repetida
o porque el contenido es demasiado corto.
"""


@dataclass
class ValidationResult:
    """Resultado de validación de un documento del corpus."""
    is_valid: bool
    reason: Optional[str] = None


class CorpusQualityGate:
    """Compuerta de calidad que filtra documentos antes de persistirlos.

    La uso para evitar basura repetida o demasiado corta dentro del corpus.
    """

    def __init__(self, min_content_chars: int = 600):
        """Configura el umbral mínimo de longitud del contenido."""
        self.min_content_chars = min_content_chars
        self._seen_urls = set()
        self._seen_fingerprints = set()

    def register_existing(self, doc: Dict):
        """Registra documentos ya existentes para no volver a aceptarlos.

        Esto ayuda cuando el crawler se reanuda sobre un corpus que ya tiene
        parte del trabajo hecho.
        """
        url = str(doc.get("url", "")).strip().lower()
        content = str(doc.get("content", ""))
        if url:
            self._seen_urls.add(url)
        if content:
            self._seen_fingerprints.add(text_fingerprint(content))

    def validate(self, doc: Dict) -> ValidationResult:
        """Valida la estructura y calidad mínima del documento.

        Reglas principales:
        - campos obligatorios presentes,
        - idioma soportado,
        - longitud mínima,
        - URL no duplicada,
        - contenido no duplicado.
        """
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
