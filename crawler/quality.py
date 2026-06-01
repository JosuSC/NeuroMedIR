import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Optional

from .utils import text_fingerprint


"""
quality.py — Reglas simples de calidad para el corpus.

Prefiero que esta lógica sea transparente: si un documento se rechaza,
quiero poder decir rápidamente si fue por idioma, duplicado, URL repetida
o porque el contenido es demasiado corto.
"""


BOILERPLATE_PATTERNS = [
    r"all rights reserved",
    r"terms of use",
    r"privacy policy",
    r"copyright",
    r"unauthorized",
    r"artificial intelligence",
    r"ai systems",
    r"legal action",
]

NAVIGATION_PATTERNS = [
    r"see also",
    r"related topics",
    r"browse all",
    r"all topics",
    r"drug information",
    r"sitemap",
]

@dataclass
class ValidationResult:
    """Resultado de validación de un documento del corpus."""
    is_valid: bool
    reason: Optional[str] = None


class CorpusQualityGate:
    """Compuerta de calidad que filtra documentos antes de persistirlos.

    La uso para evitar basura repetida o demasiado corta dentro del corpus.
    """
    def __init__(self, min_content_chars: int = 600, relaxed: bool = False):
        """Configura el umbral mínimo de longitud del contenido.

        Args:
            relaxed: Si es True (modo expansión web), se omiten los filtros
                heurísticos de portada/navegación/boilerplate que suelen
                rechazar artículos válidos provenientes de páginas de
                resultados de búsqueda. Se conservan los filtros esenciales:
                campos obligatorios, idioma, longitud mínima y deduplicación.
        """
        self.min_content_chars = min_content_chars
        self.relaxed = relaxed
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

    def _contains_boilerplate(self, text: str) -> bool:
        lowered = text.lower()

        matches = sum(
            1
            for pattern in BOILERPLATE_PATTERNS
            if re.search(pattern, lowered)
        )

        return matches >= 2
    
    def _looks_like_navigation_page(self, text: str) -> bool:
        lowered = text.lower()

        matches = sum(
            1
            for pattern in NAVIGATION_PATTERNS
            if re.search(pattern, lowered)
        )

        short_lines = [
            line.strip()
            for line in text.splitlines()
            if 0 < len(line.strip()) < 80
        ]

        if matches >= 3:
            return True

        if len(short_lines) > 200:
            return True

        return False    
    
    def _is_portal_or_landing_page(self, text: str) -> bool:
        """Detecta páginas portada, índices y hubs de navegación."""
        # Señales fuertes de página portada
        PORTAL_SIGNALS = [
            r"leer (todo|más)",
            r"read (more|all)",
            r"ver (todo|más)",
            r"search search",
            r"haz(te)? socio",
            r"dona(r)?",
            r"suscri(bete|base)",
            r"newsletter",
            r"últimas noticias",
            r"noticias destacadas",
            r"en portada",
            r"política de cookies",
            r"acepta(r)? cookies",
            r"gestionar (el )?consentimiento",
        ]
        lowered = text.lower()
        signal_count = sum(
            1 for p in PORTAL_SIGNALS
            if re.search(p, lowered)
        )
        # Si tiene 2 o más señales de portada, es ruido
        if signal_count >= 2:
            return True

        # Ratio de oraciones completas: texto real tiene oraciones largas
        sentences = [
            s.strip() for s in re.split(r'[.!?]', text)
            if len(s.strip()) > 40
        ]
        total_words = len(text.split())
        if total_words > 100 and len(sentences) < 3:
            return True

        # Detectar patrones repetidos de hub/listado
        leer_todo_count = len(re.findall(r'\bleer (todo|más)\b', lowered))
        read_more_count = len(re.findall(r'\bread (more|all)\b', lowered))
        ir_al_articulo_count = len(re.findall(r'\bir al artículo\b', lowered))
        min_lectura_count = len(re.findall(r'\bmin de lectura\b', lowered))
        if leer_todo_count >= 3 or read_more_count >= 3:
            return True
        if ir_al_articulo_count >= 2 or min_lectura_count >= 4:
            return True
        
        return False
    
    def _has_excessive_repetition(self, text: str) -> bool:
        words = re.findall(r"\w+", text.lower())

        if len(words) < 200:
            return False

        counter = Counter(words)

        top_10_ratio = (
            sum(freq for _, freq in counter.most_common(10))
            / len(words)
        )

        return top_10_ratio > 0.30
    
    
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

        # Validar que el contenido coincida con el idioma declarado
        content_lower = doc["content"].lower()
        es_markers = {"el ", "la ", "los ", "las ", "de ", "en ", "que ", "por ", "con ", "una "}
        en_markers = {"the ", "and ", "for ", "with ", "this ", "that ", "from ", "have ", "are ", "not "}
        es_count = sum(1 for m in es_markers if m in content_lower)
        en_count = sum(1 for m in en_markers if m in content_lower)
        if doc["language"] == "es" and en_count > es_count + 3:
            return ValidationResult(False, "language_mismatch_en_as_es")
        if doc["language"] == "en" and es_count > en_count + 3:
            return ValidationResult(False, "language_mismatch_es_as_en")

        if len(doc["content"]) < self.min_content_chars:
            return ValidationResult(False, "content_too_short")

        # En modo relajado (expansión web) se omiten los filtros heurísticos
        # que tienden a rechazar artículos válidos por falsos positivos.
        if not self.relaxed:
            if self._contains_boilerplate(doc["content"]):
                return ValidationResult(False, "boilerplate_content")

            if self._looks_like_navigation_page(doc["content"]):
                return ValidationResult(False, "navigation_page")

            if self._is_portal_or_landing_page(doc["content"]):
                return ValidationResult(False, "portal_or_landing_page")

            if self._has_excessive_repetition(doc["content"]):
                return ValidationResult(False, "excessive_repetition")

        normalized_url = doc["url"].strip().lower()
        if normalized_url in self._seen_urls:
            return ValidationResult(False, "duplicate_url")

        fp = text_fingerprint(doc["content"])
        if fp in self._seen_fingerprints:
            return ValidationResult(False, "duplicate_content")

        self._seen_urls.add(normalized_url)
        self._seen_fingerprints.add(fp)
        return ValidationResult(True, None)
