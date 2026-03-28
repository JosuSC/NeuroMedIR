"""
retriever.py — Main facade for the NeuroMedIR Retrieval Module.

This is the central orchestrator that implements the full retrieval pipeline:

    query
     ↓
    QueryProcessor (normalize, tokenize)
     ↓
    ┌────────────────────┬──────────────────────────┐
    │  BM25 Lexical      │  NN → Embedding → FAISS  │
    │  (exact keywords)  │  (semantic understanding) │
    └────────┬───────────┴────────────┬─────────────┘
             └────────────┬───────────┘
                          ↓
                   Score Fusion (RRF)
                          ↓
                    Final Ranking
                          ↓
                  Enriched Results

Architectural principles (from agent.md):
    - Modularidad estricta: cada módulo con una responsabilidad principal
    - Interfaces claras y contratos de entrada/salida explícitos
    - No mezclar lógica de negocio con IO sin justificación

This module depends on the Indexing module for:
    - TextEncoder (shared neural model for query embedding)
    - BM25Index (lexical index)
    - FAISSHNSWIndex (vector index)
    - TextCleaner (preprocessing, reused via QueryProcessor)
"""

import json
import logging
import os
from typing import List, Dict, Optional

from indexing.indexer import Indexer
from indexing.configs import settings as idx_settings

from .query_processor import QueryProcessor
from .neural_ranker import NeuralRanker
from .fusion import fuse
from .configs import settings as ret_settings

logger = logging.getLogger(__name__)


class Retriever:
    """
    Hybrid retrieval engine combining lexical and neural search with score fusion.

    Usage:
        retriever = Retriever()       # Loads indices from disk
        results = retriever.retrieve("síntomas de diabetes tipo 2")

    Each result in the returned list contains:
        - doc_id: int
        - score: float (fused score, higher is better)
        - title: str (document title)
        - snippet: str (first 300 chars of content)
        - source: str (domain)
        - url: str (original URL)
    """

    def __init__(self):
        """
        Initializes all sub-components and loads persisted indices.
        """
        logger.info("Initializing Retriever...")

        # 1. Initialize the shared Indexer (loads encoder + indices)
        self._indexer = Indexer()
        loaded = self._indexer.load_indices()
        if not loaded:
            raise RuntimeError(
                "Failed to load indices. Run the indexing pipeline first "
                "(python -m indexing.tests.test_indexer)."
            )

        # 2. Query processor (reuses the same TextCleaner as the indexer)
        self._query_processor = QueryProcessor()

        # 3. Neural ranker (wraps the encoder + FAISS index)
        self._neural_ranker = NeuralRanker(
            encoder=self._indexer.encoder,
            vector_index=self._indexer.semantic_index,
            cross_encoder_model=ret_settings.CROSS_ENCODER_MODEL,
        )

        # 4. Load document metadata for enriching results
        self._doc_store = self._load_document_store()

        logger.info(
            f"Retriever ready. Documents in store: {len(self._doc_store)}. "
            f"Fusion strategy: {ret_settings.FUSION_STRATEGY}."
        )

    def _load_document_store(self) -> Dict[int, Dict]:
        """
        Loads processed documents from disk into a dict keyed by doc_id.
        Used to enrich search results with titles, snippets, and URLs.
        """
        store = {}
        processed_dir = idx_settings.PROCESSED_DATA_DIR
        if not processed_dir.exists():
            logger.warning(f"Processed data directory not found: {processed_dir}")
            return store

        for filename in os.listdir(processed_dir):
            if filename.endswith(".json"):
                filepath = processed_dir / filename
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        doc = json.load(f)
                    doc_id = doc.get("id")
                    if doc_id is not None:
                        store[doc_id] = doc
                except (json.JSONDecodeError, OSError) as e:
                    logger.error(f"Failed to load {filepath}: {e}")

        logger.info(f"Loaded {len(store)} documents into the document store.")
        return store

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        strategy: str = None,
    ) -> List[Dict]:
        """
        Full retrieval pipeline: process → search (parallel lanes) → fuse → rank → enrich.

        Args:
            query: Raw user query in Spanish or English.
            top_k: Number of final results (defaults to config FINAL_TOP_K).
            strategy: Fusion strategy override ("rrf" or "weighted").

        Returns:
            List of result dicts sorted by relevance, each containing:
            {"doc_id", "score", "rank", "title", "snippet", "source", "url"}
        """
        top_k = top_k or ret_settings.FINAL_TOP_K

        # Step 1: Process query
        logger.info(f"Processing query: '{query}'")
        processed = self._query_processor.process(query)

        # Step 2a: Lexical retrieval (BM25)
        logger.info("Running lexical retrieval (BM25)...")
        lexical_results = self._indexer.lexical_index.search(
            processed["lexical_tokens"],
            top_k=ret_settings.LEXICAL_TOP_K,
        )
        logger.info(f"  BM25 returned {len(lexical_results)} candidates.")

        # Step 2b: Semantic retrieval (NN → Embedding → FAISS)
        logger.info("Running semantic retrieval (NN → FAISS)...")
        semantic_results = self._neural_ranker.score(
            processed["semantic_text"],
            top_k=ret_settings.SEMANTIC_TOP_K,
        )
        logger.info(f"  FAISS returned {len(semantic_results)} candidates.")

        # Step 3: Fusion
        logger.info("Fusing results...")
        fused_results = fuse(
            lexical_results,
            semantic_results,
            strategy=strategy,
            top_k=top_k,
        )
        logger.info(f"  Fusion produced {len(fused_results)} ranked results.")

        # Step 4: Enrich with document metadata
        enriched_results = self._enrich_results(fused_results)

        return enriched_results

    def retrieve_lexical_only(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Retrieves using only the BM25 lexical index (for comparison/debugging).
        """
        processed = self._query_processor.process(query)
        results = self._indexer.lexical_index.search(
            processed["lexical_tokens"], top_k=top_k
        )
        return self._enrich_results(results)

    def retrieve_semantic_only(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Retrieves using only the neural/semantic index (for comparison/debugging).
        """
        processed = self._query_processor.process(query)
        results = self._neural_ranker.score(
            processed["semantic_text"], top_k=top_k
        )
        return self._enrich_results(results)

    def _enrich_results(self, results: List[Dict]) -> List[Dict]:
        """
        Attaches document metadata (title, snippet, source, url) to each result
        and adds a 1-based rank field.
        """
        enriched = []
        for rank, result in enumerate(results, start=1):
            doc_id = result["doc_id"]
            doc = self._doc_store.get(doc_id, {})

            content = doc.get("content", "")
            snippet = content[:300] + "..." if len(content) > 300 else content

            enriched.append({
                "rank": rank,
                "doc_id": doc_id,
                "score": round(result["score"], 6),
                "title": doc.get("title", "Unknown"),
                "snippet": snippet,
                "source": doc.get("source", "Unknown"),
                "url": doc.get("url", ""),
            })

        return enriched
