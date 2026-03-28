"""
retriever.py — Main facade for the NeuroMedIR Hybrid Retrieval Module.

Implements the canonical hybrid IR pipeline:

    query (raw string)
     ↓
    preprocess_query(query)          → {lexical_tokens, semantic_text}
     ↓
    ┌────────────────────────────────┬─────────────────────────────────┐
    │ search_bm25(tokens)            │ generate_embedding(text)        │
    │ → lexical candidates           │ → dense vector                  │
    │                                │ ↓                               │
    │                                │ search_faiss(vector)            │
    │                                │ → semantic candidates           │
    └───────────────┬────────────────┴────────────────┬───────────────┘
                    ↓                                 ↓
             normalize_scores()                normalize_scores()
                    ↓                                 ↓
                    └─────────────┬────────────────────┘
                                  ↓
                       fuse_results(lex, sem)
                                  ↓
                          rank_results()
                                  ↓
                        top-k enriched results

Design principles (from agent.md):
    - Dependency injection for all components (fixes P1)
    - Every pipeline step is a public, independently callable method (fixes P6)
    - I/O separated into DocumentStore (fixes P5)
    - Latency measured per stage (fixes P7)
"""

import time
import logging
from typing import List, Dict, Optional

from indexing.preprocess.text_cleaner import TextCleaner
from indexing.lexical_index.bm25_index import BM25Index
from indexing.vector_index.faiss_hnsw import FAISSHNSWIndex
from indexing.multimodal.text_encoder import TextEncoder
from indexing.storage.index_io import IndexStorage
from indexing.configs import settings as idx_settings

from .query_processor import QueryProcessor
from .semantic_search import SemanticSearch
from .document_store import DocumentStore
from .fusion import fuse_results, normalize_scores, rank_results
from .configs import settings as ret_settings

logger = logging.getLogger(__name__)


class Retriever:
    """
    Hybrid retrieval engine combining lexical (BM25) and neural (FAISS/NN)
    search with score fusion and ranking.

    All pipeline steps are exposed as public methods for independent use,
    testing, and debugging.

    Usage:
        retriever = Retriever.from_disk()
        results = retriever.retrieve("síntomas de diabetes tipo 2")

    Each result contains:
        rank, doc_id, score, title, snippet, source, url
    """

    def __init__(
        self,
        lexical_index: BM25Index,
        vector_index: FAISSHNSWIndex,
        encoder: TextEncoder,
        doc_store: DocumentStore,
        cleaner: TextCleaner = None,
    ):
        """
        Dependency-injected constructor (fixes P1).

        Args:
            lexical_index: Pre-loaded BM25 index.
            vector_index: Pre-loaded FAISS HNSW index.
            encoder: Pre-loaded multilingual text encoder.
            doc_store: Pre-loaded document store for result enrichment.
            cleaner: Shared TextCleaner (creates new one if None).
        """
        self._cleaner = cleaner or TextCleaner()
        self._query_processor = QueryProcessor(cleaner=self._cleaner)
        self._lexical_index = lexical_index
        self._semantic_search = SemanticSearch(encoder=encoder, vector_index=vector_index)
        self._doc_store = doc_store
        self._encoder = encoder

        logger.info(
            f"Retriever ready. Documents: {doc_store.count}. "
            f"Fusion: {ret_settings.FUSION_STRATEGY}."
        )

    @classmethod
    def from_disk(cls) -> "Retriever":
        """
        Factory method: loads all components from persisted state on disk.
        This is the standard way to create a Retriever for production use.
        """
        logger.info("Loading Retriever components from disk...")

        # Load encoder
        encoder = TextEncoder(idx_settings.EMBEDDING_MODEL_NAME)

        # Load indices
        cleaner = TextCleaner()
        lexical_index = BM25Index(
            k1=idx_settings.BM25_PARAMS["k1"],
            b=idx_settings.BM25_PARAMS["b"],
        )
        vector_index = FAISSHNSWIndex(
            dimension=idx_settings.EMBEDDING_DIM,
            m=idx_settings.HNSW_M,
            ef_construction=idx_settings.HNSW_EF_CONSTRUCTION,
        )

        storage = IndexStorage(str(idx_settings.INDEX_STORAGE_DIR))
        lex_ok = storage.load_lexical(lexical_index)
        vec_ok = storage.load_vector(vector_index)

        if not (lex_ok and vec_ok):
            raise RuntimeError(
                "Failed to load indices from disk. "
                "Run the indexing pipeline first: python -m indexing.tests.test_indexer"
            )

        # Load document store
        doc_store = DocumentStore(idx_settings.PROCESSED_DATA_DIR)

        return cls(
            lexical_index=lexical_index,
            vector_index=vector_index,
            encoder=encoder,
            doc_store=doc_store,
            cleaner=cleaner,
        )

    # -----------------------------------------------------------------------
    # Public API — Every pipeline step is individually callable (fixes P6)
    # -----------------------------------------------------------------------

    def preprocess_query(self, query: str) -> Dict[str, object]:
        """
        Step 1: Preprocess a raw query for both retrieval lanes.

        Returns:
            {"raw": str, "lexical_tokens": list, "semantic_text": str}
        """
        return self._query_processor.process(query)

    def search_bm25(self, query_tokens: list, top_k: int = None) -> List[Dict]:
        """
        Step 2a: Lexical retrieval via BM25 inverted index.

        Args:
            query_tokens: Tokenized query from preprocess_query().
            top_k: Number of candidates (defaults to config).

        Returns:
            List of {"doc_id": int, "score": float} scored by BM25.
        """
        top_k = top_k or ret_settings.LEXICAL_TOP_K
        if not query_tokens:
            return []
        return self._lexical_index.search(query_tokens, top_k=top_k)

    def generate_embedding(self, text: str):
        """
        Step 2b-i: Generate a dense embedding vector from text via the NN.

        Args:
            text: Semantic-ready text from preprocess_query().

        Returns:
            numpy array of shape (embedding_dim,).
        """
        return self._semantic_search.generate_embedding(text)

    def search_faiss(self, query_vector, top_k: int = None) -> List[Dict]:
        """
        Step 2b-ii: Search FAISS HNSW index for nearest neighbors.

        Args:
            query_vector: Dense vector from generate_embedding().
            top_k: Number of candidates (defaults to config).

        Returns:
            List of {"doc_id": int, "score": float} with similarity scores.
        """
        top_k = top_k or ret_settings.SEMANTIC_TOP_K
        return self._semantic_search.search_faiss(query_vector, top_k=top_k)

    # normalize_scores and rank_results are importable from fusion.py directly,
    # but we also expose them here for convenience.

    @staticmethod
    def normalize_scores(results: List[Dict]) -> List[Dict]:
        """Step 3: Normalize scores to [0, 1] range."""
        return normalize_scores(results)

    @staticmethod
    def fuse_results(
        lexical_results: List[Dict],
        semantic_results: List[Dict],
        strategy: str = None,
    ) -> List[Dict]:
        """Step 4: Fuse results from both retrieval lanes."""
        return fuse_results(lexical_results, semantic_results, strategy=strategy)

    @staticmethod
    def rank_results(results: List[Dict], top_k: int = 10) -> List[Dict]:
        """Step 5: Sort by score descending and truncate to top_k."""
        return rank_results(results, top_k=top_k)

    # -----------------------------------------------------------------------
    # Orchestrated Retrieval (full pipeline)
    # -----------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        strategy: str = None,
    ) -> List[Dict]:
        """
        Full hybrid retrieval pipeline with latency measurement.

        Pipeline:
            preprocess → search_bm25 + (generate_embedding → search_faiss)
            → fuse → rank → enrich

        Args:
            query: Raw user query in Spanish or English.
            top_k: Number of final results (defaults to config FINAL_TOP_K).
            strategy: Fusion strategy override ("rrf" or "weighted").

        Returns:
            List of enriched result dicts sorted by relevance, each containing:
            {"rank", "doc_id", "score", "title", "snippet", "source", "url",
             "latency_ms"}
        """
        top_k = top_k or ret_settings.FINAL_TOP_K
        t_start = time.perf_counter()

        # Step 1: Preprocess
        t0 = time.perf_counter()
        processed = self.preprocess_query(query)
        t_preprocess = time.perf_counter() - t0

        # Step 2a: Lexical retrieval (BM25)
        t0 = time.perf_counter()
        lexical_results = self.search_bm25(processed["lexical_tokens"])
        t_bm25 = time.perf_counter() - t0

        # Step 2b: Semantic retrieval (NN → Embedding → FAISS)
        t0 = time.perf_counter()
        embedding = self.generate_embedding(processed["semantic_text"])
        t_embed = time.perf_counter() - t0

        t0 = time.perf_counter()
        semantic_results = self.search_faiss(embedding)
        t_faiss = time.perf_counter() - t0

        # Step 3+4: Fuse (normalization handled internally by strategy)
        t0 = time.perf_counter()
        fused = self.fuse_results(lexical_results, semantic_results, strategy=strategy)
        t_fusion = time.perf_counter() - t0

        # Step 5: Rank
        ranked = self.rank_results(fused, top_k=top_k)

        t_total = time.perf_counter() - t_start

        # Log latency per stage
        logger.info(
            f"Retrieval completed in {t_total*1000:.1f}ms — "
            f"preprocess: {t_preprocess*1000:.1f}ms, "
            f"BM25: {t_bm25*1000:.1f}ms ({len(lexical_results)} hits), "
            f"embed: {t_embed*1000:.1f}ms, "
            f"FAISS: {t_faiss*1000:.1f}ms ({len(semantic_results)} hits), "
            f"fusion: {t_fusion*1000:.1f}ms → {len(ranked)} results"
        )

        # Step 6: Enrich with document metadata
        enriched = self._enrich_results(ranked)

        # Attach total latency to the response
        for r in enriched:
            r["latency_ms"] = round(t_total * 1000, 1)

        return enriched

    def retrieve_lexical_only(self, query: str, top_k: int = 10) -> List[Dict]:
        """Retrieves using only BM25 (for comparison/debugging)."""
        processed = self.preprocess_query(query)
        results = self.search_bm25(processed["lexical_tokens"], top_k=top_k)
        return self._enrich_results(results)

    def retrieve_semantic_only(self, query: str, top_k: int = 10) -> List[Dict]:
        """Retrieves using only the NN/FAISS lane (for comparison/debugging)."""
        processed = self.preprocess_query(query)
        results = self._semantic_search.search(processed["semantic_text"], top_k=top_k)
        return self._enrich_results(results)

    # -----------------------------------------------------------------------
    # Private Helpers
    # -----------------------------------------------------------------------

    def _enrich_results(self, results: List[Dict]) -> List[Dict]:
        """
        Attaches document metadata (title, snippet, source, url) to each result
        and adds a 1-based rank field.
        """
        enriched = []
        for rank, result in enumerate(results, start=1):
            doc_id = result["doc_id"]
            doc = self._doc_store.get(doc_id) or {}

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
