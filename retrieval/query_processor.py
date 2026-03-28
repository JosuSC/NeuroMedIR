"""
query_processor.py — Prepares raw user queries for both retrieval pipelines.

Responsibility:
    Takes a raw query string (in Spanish or English) and produces:
    1. Tokenized form for BM25 lexical search.
    2. Clean text form for the neural encoder (semantic search).

Design decision:
    Accepts a TextCleaner via dependency injection to guarantee that queries
    are processed with the EXACT same pipeline instance as documents.
    Any mismatch between document preprocessing and query preprocessing
    degrades retrieval quality silently.
"""

import logging
from typing import Dict

from indexing.preprocess.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)


class QueryProcessor:
    """
    Transforms a raw query into representations suitable for each retrieval lane.
    """

    def __init__(self, cleaner: TextCleaner = None):
        """
        Args:
            cleaner: Shared TextCleaner instance. If None, creates a new one.
        """
        self.cleaner = cleaner or TextCleaner()

    def process(self, raw_query: str) -> Dict[str, object]:
        """
        Processes a raw query string and returns a dictionary with both
        the lexical tokens and the semantic-ready text.

        Args:
            raw_query: The user's search query as-is.

        Returns:
            {
                "raw": str,              # Original query (for logging/display)
                "lexical_tokens": list,  # Tokens for BM25
                "semantic_text": str     # Cleaned text for the NN encoder
            }

        Raises:
            ValueError: If the query is empty or None.
        """
        if not raw_query or not raw_query.strip():
            raise ValueError("Query cannot be empty.")

        raw_query = raw_query.strip()

        lexical_tokens = self.cleaner.preprocess_for_lexical(raw_query)
        semantic_text = self.cleaner.preprocess_for_semantic(raw_query)

        logger.debug(
            f"Query processed — tokens: {len(lexical_tokens)}, "
            f"semantic_len: {len(semantic_text)} chars"
        )

        return {
            "raw": raw_query,
            "lexical_tokens": lexical_tokens,
            "semantic_text": semantic_text,
        }
