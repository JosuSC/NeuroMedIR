"""
document_classifier.py — Categoriza documentos extraídos basado en dominio y contenido.

Responsabilidades:
    1. Detectar tipo de documento (article, topic, resource, etc.) por dominio.
    2. Validar estructura mínima del documento contre schema.
    3. Enriquecer metadatos del documento con categoría y validez.
"""

import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """Clasifica y valida documentos extraídos del crawling."""

    # Mapeos de dominio a categoría por defecto
    DOMAIN_CATEGORIES = {
        "medlineplus.gov": "health_topic",
        "pubmed.ncbi.nlm.nih.gov": "research_article",
        "who.int": "health_guideline",
        "ncbi.nlm.nih.gov": "research",
    }

    # Palabras clave por categoría para detectar tipo
    CATEGORY_KEYWORDS = {
        "health_topic": ["symptom", "síntoma", "treatment", "tratamiento", "cause", "causa"],
        "research_article": ["abstract", "resumen", "author", "autor", "study", "estudio"],
        "health_guideline": ["recommendation", "recomendación", "guideline", "guía", "standard", "estándar"],
        "news": ["news", "noticia", "update", "actualización", "report", "reporte"],
    }

    @staticmethod
    def infer_category(source: str, content: str) -> str:
        """
        Infiere la categoría del documento basado en dominio y palabras clave.

        Args:
            source: Dominio del documento (ej. medlineplus.gov).
            content: Contenido del documento.

        Returns:
            Categoría como string (ej. "health_topic", "research_article").
        """
        # Primero: usar mapeo de dominio
        for domain, category in DocumentClassifier.DOMAIN_CATEGORIES.items():
            if domain in source.lower():
                return category

        # Segundo: usar palabras clave en contenido
        content_lower = content.lower() if content else ""
        for category, keywords in DocumentClassifier.CATEGORY_KEYWORDS.items():
            if any(kw in content_lower for kw in keywords):
                return category

        # Default: generic
        return "generic_content"

    @staticmethod
    def validate_document_schema(doc: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Valida que un documento tenga la estructura mínima esperada.

        Args:
            doc: Documento como diccionario.

        Returns:
            (is_valid, error_message)
            - Si valid: (True, "")
            - Si inválido: (False, descripción del error)
        """
        required_fields = ["title", "content", "source", "url"]

        # Verificar campos obligatorios
        for field in required_fields:
            if field not in doc:
                return False, f"Missing required field: '{field}'"
            if not isinstance(doc[field], str):
                return False, f"Field '{field}' must be string, got {type(doc[field])}"

        # Verificar que no sean vacíos
        if not doc["title"].strip():
            return False, "Field 'title' cannot be empty"
        if not doc["content"].strip():
            return False, "Field 'content' cannot be empty"
        if not doc["url"].strip():
            return False, "Field 'url' cannot be empty"

        # Verificar longitud mínima de contenido (evita páginas boilerplate)
        if len(doc["content"]) < 100:
            return False, f"Content too short ({len(doc['content'])} chars, min 100)"

        return True, ""

    @staticmethod
    def enrich_document(doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriquece un documento con metadatos de categoría y valididad.

        Args:
            doc: Documento extraído del crawler.

        Returns:
            Documento enriquecido con campos 'category', 'is_valid', 'validation_error'.
        """
        is_valid, error_msg = DocumentClassifier.validate_document_schema(doc)

        doc["is_valid"] = is_valid
        doc["validation_error"] = error_msg if error_msg else None

        if is_valid:
            doc["category"] = DocumentClassifier.infer_category(
                doc.get("source", ""),
                doc.get("content", "")
            )
        else:
            doc["category"] = None
            logger.warning(f"Invalid document: {error_msg}")

        return doc
