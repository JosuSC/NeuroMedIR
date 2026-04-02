"""
document_store.py — Loads and caches processed documents for result enrichment.

Separates I/O logic from the Retriever (fixes P5).
Single responsibility: read documents from disk, cache them in memory,
and provide fast lookup by doc_id.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DocumentStore:
    """
    In-memory cache of processed documents, loaded once from disk.
    Used exclusively for enriching search results with metadata
    (title, content snippet, source, url).
    """

    def __init__(self, processed_dir: Path):
        """
        Args:
            processed_dir: Path to the directory containing processed JSON docs.
        """
        self._store: Dict[int, Dict] = {}
        self._processed_dir = processed_dir
        self._load()

    def _load(self):
        """Loads all processed JSON documents recursively into memory."""
        if not self._processed_dir.exists():
            logger.warning(f"Processed data directory not found: {self._processed_dir}")
            return

        loaded = 0
        errors = 0
        for filepath in self._processed_dir.rglob("*.json"):
            if not filepath.is_file():
                continue
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    doc = json.load(f)
                doc_id = doc.get("id")
                if doc_id is not None:
                    self._store[doc_id] = doc
                    loaded += 1
                else:
                    logger.warning(f"Document without 'id' field: {filepath}")
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Failed to load {filepath}: {e}")
                errors += 1

        logger.info(
            f"DocumentStore loaded {loaded} documents "
            f"({errors} errors) from {self._processed_dir}"
        )

    def get(self, doc_id: int) -> Optional[Dict]:
        """Returns the document dict for a given doc_id, or None."""
        return self._store.get(doc_id)

    def get_text(self, doc_id: int) -> str:
        """Returns the content text for a given doc_id, or empty string."""
        doc = self._store.get(doc_id)
        if doc:
            return doc.get("content", "")
        return ""

    def get_texts(self, doc_ids: list) -> Dict[int, str]:
        """Returns a mapping of doc_id → content text for a list of IDs."""
        return {
            doc_id: self.get_text(doc_id)
            for doc_id in doc_ids
            if self.get(doc_id) is not None
        }

    @property
    def count(self) -> int:
        """Number of documents in the store."""
        return len(self._store)
